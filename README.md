# Google Careers Job Search Automation






<img width="1752" height="746" alt="Screenshot 2025-11-12 135538" src="https://github.com/user-attachments/assets/d37790b9-e784-46e3-9d8f-2f4f6067d0a3" />






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


Setup (for OpenAI LLM Mode)
1. Get your OpenAI API key

Sign up or log in at:
👉 https://platform.openai.com/account/api-keys



2. Add your key to a .env file (recommended)

Create a file named .env in your project folder:

OPENAI_API_KEY=sk-your-api-key-here


⚠️ Never share or commit your API key.
Add .env to your .gitignore.



Run the App
streamlit run google_jobs_automation.py
Then open the local URL Streamlit prints (usually http://localhost:8501).

🧮 Example Queries

Try entering:

Internships in Bangalore for pursuing degree

Early roles in Hyderabad remote

Full-time software engineer jobs in London

Intern roles for bachelor's degree students


🧩 Output Example

For a query like:

“Internships in Bangalore pursuing degree”

The app will:

1️⃣ Extract filters →
{
  "location": "Bangalore, India",
  "target_level": "INTERN_AND_APPRENTICE",
  "degree": "PURSUING_DEGREE"
}

2️⃣ Build a URL →
https://www.google.com/about/careers/applications/jobs/results/?location=Bangalore%2C+India&target_level=INTERN_AND_APPRENTICE&degree=PURSUING_DEGREE

3️⃣ Fetch and list matching job titles, locations, and links.
🧠 Author

Developed by Manohar Savarapu
Built with ❤️ using Streamlit
 and OpenAI
