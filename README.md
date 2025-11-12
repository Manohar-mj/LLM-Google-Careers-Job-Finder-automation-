# Google Careers Job Search Automation

A **Streamlit web app** that automates job searches on **Google Careers** using a natural-language query.

It can:
- Accept a user query like:  
  _"Internships in Bangalore for pursuing degree"_
- Optionally use an **LLM (OpenAI)** to extract structured filters  
- Build a valid Google Careers search URL  
- Fetch and parse job listings (titles, location, link, snippets)

---

## 🚀 Features

- 🧠 **LLM-based filter extraction** using OpenAI GPT models (optional)  
- 🧩 **Heuristic parser** (no API key needed)  
- 🌐 **Google Careers scraping** (public results pages)  
- ⚙️ **Streamlit UI** for quick use and testing  

---

## 🧰 Requirements

- Python **3.9+**
- Required packages:

```bash
pip install streamlit requests beautifulsoup4 openai python-dotenv
