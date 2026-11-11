# 🎓 Atlas Funding — Autonomous Scholarship Intelligence Crawler

Built for the **EDXSO AI Engineer Intern — Assignment 2**. This system is an end-to-end, multi-run Scholarship Intelligence Engine that continuously **Discovers → Crawls → Extracts → Verifies → Scores → Stores → Updates** authentic scholarship opportunities for Indian students across **Government, Universities, Corporate CSR, NGO/Trusts, and International** providers.

---

## 📑 Technical Note (Architecture & Methodology)

### 1. System Architecture & Technology Stack

- **Step 1: Discovery & Source Classifier (`src/discovery.py`)**
  Crawls seed portals and classifies domains into `Government`, `University`, `Corporate CSR`, `NGO/Trust`, and `International`. Filters out third-party aggregators (`Buddy4Study`, `Shiksha`, `Careers360`, `Collegedunia`) from being treated as primary authoritative sources.
- **Step 2: Resilient Primary-Source Crawler (`src/crawler.py`)**
  Fetches official HTML/text from primary sources and computes SHA-256 content hashes (`raw_content_hash`) for change detection.
- **Step 3: Anti-Hallucination 20-Field Extractor (`src/extractor.py`)**
  Extracts the structured 20-field Atlas schema and maps verbatim substring quotes (`evidence_map`). Enforces a strict `"Not specified"` default whenever attributes (income limit, age limit, gender criteria) are absent in the primary source text.
- **Step 4: Deterministic 6-Point Verification & Confidence Engine (`src/verifier.py`)**
  Computes an explainable mathematical confidence score (`0.0%` to `100.0%`) from verifiable evidence without arbitrary LLM guessing. Assigns `VERIFIED` (>=95.0%) vs `REVIEW_REQUIRED` (<95.0%) and computes lifecycle status: `ACTIVE`, `EXPIRING_SOON`, `EXPIRED`, `REVIEW_REQUIRED`, or `NO_LONGER_VERIFIABLE`.
- **Step 5: SQLite State & Non-Destructive Change Detection Engine (`src/database.py`)**
  Retains `old_value`, `new_value`, `date_detected`, `official_source_url`, and `evidence_quote` across repeated crawl runs in the `change_history` table.

**Free / Open-Source Stack Used:** Python 3, `requests`, `BeautifulSoup4`, `SQLite3`, `Pandas`, `Streamlit`, `Rich` CLI. Zero paid APIs or paid scraping services.

---

### 2. Discovery & Source Classification Methodology
Instead of relying on static aggregator scraping, `ScholarshipDiscoveryEngine` starts from authoritative seed portals (`scholarships.gov.in`, `aicte-india.org`, `ugc.gov.in`, `online-inspire.gov.in`, `socialjustice.gov.in`) and spiders outbound scholarship links. Every URL is passed through a domain authority classifier:
- **Authoritative Primary Domains:** `.gov.in`, `.nic.in` (`Government`), `.ac.in`, `.edu.in` (`University`), verified corporate domains (`Corporate CSR`), registered foundations (`NGO/Trust`), and bilateral bodies (`International`).
- **Aggregator Rejection:** Domains matching `buddy4study.com`, `shiksha.com`, `careers360.com`, or `collegedunia.com` are flagged as `Aggregator (Non-Authoritative)`. If a scholarship's application link points only to an aggregator or lacks an official closing date (e.g., *Kotak Kanya Scholarship* lead), its confidence score is automatically penalized below 95% and marked `REVIEW_REQUIRED`.

---

### 3. Anti-Hallucination Extraction & Evidence Traceability
A core failure mode of LLM scrapers is inventing plausible defaults (e.g., guessing an income limit of `Rs. 5 Lakh` when none exists). Our `AntiHallucinationExtractor` enforces two strict invariants:
1. **Explicit Null Handling:** Any attribute not explicitly stated in the official source notification (such as `Income Criteria` for *DST INSPIRE SHE* or *PMSS*, or `Age Criteria` for *AICTE Pragati*) is strictly recorded as `"Not specified"`.
2. **Database → Official Source → Verbatim Evidence Trace:** For every critical field (`amount_benefit`, `eligibility_summary`, `income_criteria`, `academic_requirements`, `closing_date`, `opening_date`, `documents_required`), the extractor captures the exact verbatim sentence from the official notification and stores it in `evidence_json`.

---

### 4. Deterministic Confidence-Score Methodology (Why >=95% = VERIFIED)
Rather than asking an LLM to guess a confidence percentage, `DeterministicVerificationEngine` computes a reproducible score out of **100.0 points** across 6 programmatic checks:
1. **Official Primary Source Authority (25.0 pts):** +25.0 if hosted on a verified Government, University, CSR, NGO, or International primary domain; +5.0 if third-party.
2. **Active Scheme Presence on Source (15.0 pts):** +15.0 if the scheme is actively present on the official portal and not marked discontinued/HTTP 410.
3. **Official Application URL Authenticity (10.0 pts):** +10.0 if the application link resolves to an official portal (e.g., `scholarships.gov.in`, `online-inspire.gov.in`); +2.0 if routed to an aggregator.
4. **Verbatim Substring Evidence Match for Benefit & Eligibility (20.0 pts):** Programmatically verifies `evidence_quote in raw_source_text` (+20.0 for full match).
5. **Deadline Evidence & Current Academic Cycle Support (15.0 pts):** +15.0 if the deadline is explicitly present in the raw text and corresponds to the current 2026-27 cycle.
6. **Schema Completeness & Zero-Hallucination Audit (15.0 pts):** Proportional score based on grounded extraction across core schema fields.

**Threshold Rule:** Only records scoring **>= 95.0%** are labelled **`VERIFIED`**. Anything below **95.0%** is automatically labelled **`REVIEW_REQUIRED`**.

---

### 5. Multi-Run Auto-Crawler, Change Detection & Stale Data Handling
When the crawler runs repeatedly (`Run #1` followed by `Run #2`), `upsert_scholarship_with_change_detection` compares the newly extracted fields against the existing SQLite record:
- **Change Detection:** When official corrigenda extend deadlines or update benefits (e.g., *AICTE Pragati* deadline extended from `31 October 2026` to `15 December 2026`, *HDFC Parivartan* extended from `30 September 2026` to `30 November 2026`, *NMMSS* extended from `30 September 2026` to `15 November 2026`), the system logs a `CHANGE DETECTED` entry in the `change_history` table preserving `old_value`, `new_value`, `date_detected`, `official_source_url`, and `evidence_quote`.
- **Stale / Expired / Discontinued Detection:**
  - `EXPIRED`: Scholarships whose verified closing date has passed (e.g., *Inlaks Shivdasani Scholarship* — closed `31 March 2026`; *Reliance Foundation UG* — closed `06 October 2026`).
  - `EXPIRING_SOON`: Scholarships closing within 20 days of the crawl date (e.g., *DST INSPIRE SHE* — closing `15 November 2026`; *British Council GREAT Scholarships* — closing `20 November 2026`).
  - `NO_LONGER_VERIFIABLE`: Scholarships removed or officially discontinued by the ministry (e.g., *Maulana Azad National Fellowship (MANF)* discontinued by Ministry of Minority Affairs).

---

## 📊 Repository Output Summary (`/data`)
- **`data/scholarships_repository.csv`:** 25 real Indian scholarships across 5 source categories (`Government`, `University`, `Corporate CSR`, `NGO/Trust`, `International`).
- **`data/change_detection_log.csv`:** Non-destructive audit log of field changes across Crawl Run #1 and Crawl Run #2.
- **`data/atlas_scholarships.db`:** Full SQLite database containing `scholarships`, `change_history`, and `crawl_runs` tables.

---

## 🚀 Setup & Demonstration Instructions

1. **Install dependencies:**
   `pip install -r requirements.txt`
2. **Run the Multi-Run Auto-Crawler (Executes Run #1 Baseline + Run #2 Change Detection):**
   `python main.py`
   *(Or run individually via `python main.py --run 1` and `python main.py --run 2`)*
3. **Launch the Interactive Scholarship Intelligence Dashboard:**
   `streamlit run app.py`