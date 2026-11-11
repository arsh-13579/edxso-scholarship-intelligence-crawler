import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip().strip('"').strip("'")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    DB_PATH = "data/atlas_scholarships.db"
    VERIFIED_THRESHOLD = 95.0

    # Seed Portals for Autonomous Link-Graph Discovery
    SEED_PORTALS = [
        {"name": "National Scholarship Portal (NSP)", "url": "https://scholarships.gov.in", "type": "Government"},
        {"name": "AICTE Official Schemes", "url": "https://www.aicte-india.org/schemes/students-development-schemes", "type": "Government"},
        {"name": "UGC Scholarships & Fellowships", "url": "https://www.ugc.gov.in/page/Scholarships-and-Fellowships.aspx", "type": "Government"},
        {"name": "Department of Science & Technology (DST)", "url": "https://online-inspire.gov.in", "type": "Government"},
        {"name": "Ministry of Minority & Social Justice", "url": "https://socialjustice.gov.in/schemes", "type": "Government"}
    ]

    OFFICIAL_TLD_PATTERNS = [".gov.in", ".nic.in", ".ac.in", ".edu.in", ".org.in", ".org", ".com", ".in"]
    AGGREGATOR_DOMAINS = ["buddy4study.com", "shiksha.com", "careers360.com", "collegedunia.com", "jagranjosh.com", "weemake.in"]
