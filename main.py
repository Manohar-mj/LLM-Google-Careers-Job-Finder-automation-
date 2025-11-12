"""
google_jobs_automation.py

Single-file Streamlit app to build Google Careers search URLs from
a natural-language job query, optionally use OpenAI to extract
structured filters, fetch the Google Careers results page, and parse
basic job listings.

Python: 3.9+
Install:
    pip install streamlit requests beautifulsoup4 openai

Run:
    streamlit run google_jobs_automation.py
"""
import os
import re
import json
import urllib.parse
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()  # loads .env into environment variables


import requests
from bs4 import BeautifulSoup

try:
    import streamlit as st
except Exception:
    raise RuntimeError("This file is meant to be run with Streamlit: streamlit run google_jobs_automation.py")

# Try to import openai for LLM mode. If not installed, LLM won't be available.
USE_LLM = True
try:
    import openai
except Exception:
    USE_LLM = False

BASE_URL = "https://www.google.com/about/careers/applications/jobs/results/"

# --- Utilities: Build URL from filters ---
def build_google_careers_url(filters: Dict[str, str]) -> str:
    params = {}
    for k, v in filters.items():
        if v is None or v == "":
            continue
        if k == "has_remote":
            params[k] = "true" if str(v).lower() in ("true", "1", "yes") else "false"
        else:
            params[k] = str(v)
    query = urllib.parse.urlencode(params, safe=',')
    return BASE_URL + ("?" + query if query else "")

# --- Heuristic keyword lists & parser ---
LOCATIONS_KEYWORDS = [
    "Bangalore", "Bengaluru", "Hyderabad", "New York", "London", "remote", "Remote", "India", "USA", "UK",
]
LEVEL_KEYWORDS = {
    "intern": "INTERN_AND_APPRENTICE",
    "apprentice": "INTERN_AND_APPRENTICE",
    "early": "EARLY",
    "entry": "EARLY",
    "experienced": "EXPERIENCED",
}
DEGREE_KEYWORDS = {
    "pursuing": "PURSUING_DEGREE",
    "bachelor": "BACHELORS",
    "bachelors": "BACHELORS",
    "master": "MASTERS",
    "masters": "MASTERS",
    "phd": "DOCTORATE",
    "doctorate": "DOCTORATE",
}
EMPLOYMENT_TYPES = {
    "full time": "FULL_TIME",
    "full-time": "FULL_TIME",
    "intern": "INTERN",
    "internship": "INTERN",
}

def heuristic_extract_filters(query: str) -> Dict[str, Optional[str]]:
    q = query or ""
    filters = {"location": "", "target_level": "", "degree": "", "has_remote": "", "employment_type": "", "q": ""}

    # locations
    for loc in LOCATIONS_KEYWORDS:
        if re.search(r"\b" + re.escape(loc) + r"\b", q, re.IGNORECASE):
            if loc.lower() == "remote":
                filters["has_remote"] = "true"
            else:
                if loc.lower() in ("bengaluru", "bangalore"):
                    filters["location"] = "Bangalore, India"
                elif loc.lower() == "hyderabad":
                    filters["location"] = "Hyderabad, India"
                else:
                    filters["location"] = loc
            q = re.sub(r"\b" + re.escape(loc) + r"\b", " ", q, flags=re.IGNORECASE)

    # level
    for word, val in LEVEL_KEYWORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", q, re.IGNORECASE):
            filters["target_level"] = val
            q = re.sub(r"\b" + re.escape(word) + r"\b", " ", q, flags=re.IGNORECASE)

    # degree
    for word, val in DEGREE_KEYWORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", q, re.IGNORECASE):
            filters["degree"] = val
            q = re.sub(r"\b" + re.escape(word) + r"\b", " ", q, flags=re.IGNORECASE)

    # employment type
    for word, val in EMPLOYMENT_TYPES.items():
        if re.search(r"\b" + re.escape(word) + r"\b", q, re.IGNORECASE):
            filters["employment_type"] = val
            q = re.sub(r"\b" + re.escape(word) + r"\b", " ", q, flags=re.IGNORECASE)

    # leftover -> q
    clean_q = re.sub(r"[^A-Za-z0-9,\s.-]", " ", q).strip()
    clean_q = re.sub(r"\s{2,}", " ", clean_q)
    if clean_q:
        filters["q"] = clean_q

    return {k: v for k, v in filters.items() if v}

# --- LLM extractor using openai directly (no LangChain) ---
LLM_PROMPT = """
You are a helpful assistant that extracts structured job search filters from a user's natural language query.
Return a JSON object with keys optionally present: location, target_level, degree, has_remote (true/false), employment_type, q (keywords).
Only include keys that are clearly present.

Example:
Input: "Internships in Bangalore for pursuing degree"
Output: {"location": "Bangalore, India", "target_level": "INTERN_AND_APPRENTICE", "degree": "PURSUING_DEGREE"}

Input: {user_query}
Output:
"""

def extract_with_llm(user_query: str, openai_api_key: Optional[str]) -> Dict[str, str]:
    if not USE_LLM:
        raise RuntimeError("OpenAI python package not installed. Install it with: pip install openai")

    if not openai_api_key:
        raise RuntimeError("OpenAI API key not provided for LLM extraction.")

    # configure client
    openai.api_key = openai_api_key

    prompt = LLM_PROMPT.replace("{user_query}", json.dumps(user_query))

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract job-search filters into JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=300,
        )
    except Exception as e:
        raise RuntimeError("OpenAI request failed: " + str(e))

    assistant_text = resp["choices"][0]["message"]["content"]

    # attempt to find and parse JSON block
    m = re.search(r"\{[\s\S]*\}", assistant_text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            cleaned = assistant_text.strip().replace("'", '"')
            m2 = re.search(r"\{[\s\S]*\}", cleaned)
            if m2:
                return json.loads(m2.group(0))
            raise RuntimeError("LLM returned JSON-like text but it couldn't be parsed:\n" + assistant_text)
    else:
        try:
            return json.loads(assistant_text)
        except Exception:
            raise RuntimeError("LLM did not return a JSON object:\n" + assistant_text)

# --- Scraping Google Careers results page ---
def fetch_search_results(url: str, timeout: int = 10) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Heuristic: anchors with meaningful text
    for a in soup.find_all('a', href=True):
        href = a['href']
        title = a.get_text(strip=True)
        if not title or len(title) < 3:
            h3 = a.find('h3')
            if h3:
                title = h3.get_text(strip=True)
        if not title:
            continue

        # suspect job link patterns
        if ("/careers" in href or "/about/careers" in href or "/jobs/results" in href) and ("/" in href):
            link = urllib.parse.urljoin(BASE_URL, href)
            location = ""
            snippet = ""
            parent = a.parent
            if parent:
                texts = [t.strip() for t in parent.stripped_strings if t.strip() and t.strip() != title]
                if texts:
                    # find candidate location-like text
                    for t in texts:
                        if len(t) < 100 and any(x in t for x in (",", "India", "USA", "UK", "Remote")):
                            location = t
                            break
                    if not snippet and texts:
                        snippet = texts[0][:300]
            results.append({"title": title, "link": link, "location": location, "snippet": snippet})

    # dedupe by canonical link (strip query)
    seen = set()
    dedup = []
    for r in results:
        link = r.get("link") or ""
        norm = link.split('?')[0]
        if norm in seen:
            continue
        seen.add(norm)
        dedup.append(r)

    # fallback to parsing JSON-LD if nothing found
    if not dedup:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                jd = json.loads(script.string or "{}")
            except Exception:
                continue
            jobs = []
            if isinstance(jd, list):
                jobs = [item for item in jd if isinstance(item, dict) and item.get('@type') in ("JobPosting",)]
            elif isinstance(jd, dict) and jd.get('@type') in ("JobPosting",):
                jobs = [jd]
            for job in jobs:
                title = job.get('title') or job.get('name') or ""
                link = job.get('url') or BASE_URL
                location = ""
                jl = job.get('jobLocation')
                if isinstance(jl, dict):
                    addr = jl.get('address', {})
                    location = addr.get('addressLocality', '') or addr.get('addressRegion', '') or addr.get('addressCountry', '')
                snippet = (job.get('description') or '')[:300]
                dedup.append({"title": title, "link": link, "location": location, "snippet": snippet})

    return dedup

# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Google Careers Job Finder", layout="wide")
    st.title("Google Careers — Job Finder (automation)")

    st.markdown(
        """
Enter a natural-language query (e.g. "Internships in Bangalore pursuing degree in CS", "Early roles in Hyderabad remote pursuing degree").
You can enable LLM parsing (requires OPENAI_API_KEY in the environment) or use the built-in heuristic parser.
The app builds a Google Careers search URL and attempts to parse the results page for job titles and links.

**Note:** This scrapes public Google Careers pages based on the constructed URL. If Google changes page structure, parsing may need adjustments.
"""
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        user_query = st.text_input("Enter job search query", value="internships Bangalore pursuing degree")
    with col2:
        llm_mode = st.checkbox("Use LLM to extract filters (OpenAI)", value=False)

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if llm_mode and not openai_api_key:
        st.warning("LLM mode checked but OPENAI_API_KEY not found in environment. Will use heuristic parser instead.")
        llm_mode = False

    # Extract filters
    try:
        if llm_mode:
            filters = extract_with_llm(user_query, openai_api_key)
        else:
            filters = heuristic_extract_filters(user_query)
    except Exception as e:
        st.error("Failed to extract filters via LLM: " + str(e))
        filters = heuristic_extract_filters(user_query)

    st.subheader("Filters detected / applied")
    st.json(filters)

    url = build_google_careers_url(filters)
    st.markdown(f"**Search URL:** [{url}]({url})")

    if st.button("Search Google Careers"):
        try:
            with st.spinner("Fetching results from Google Careers..."):
                results = fetch_search_results(url)
        except Exception as e:
            st.error("Failed to fetch results: " + str(e))
            results = []

        if not results:
            st.info("No results found or parsing failed. Try different keywords or open the search URL directly.")
        else:
            st.subheader(f"Found {len(results)} result(s)")
            for r in results:
                title = r.get("title") or "(no title)"
                link = r.get("link") or url
                location = r.get("location", "")
                snippet = r.get("snippet", "")
                st.markdown(f"**[{title}]({link})**")
                if location:
                    st.write(f"Location: {location}")
                if snippet:
                    st.write(snippet)
                st.write(link)
                st.markdown("---")

if __name__ == '__main__':
    main()

