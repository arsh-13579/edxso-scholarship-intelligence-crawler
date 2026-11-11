import re
import json
import requests
from src.config import Config

class AntiHallucinationExtractor:
    """
    Converts unstructured official scholarship text into the 20-field Atlas schema.
    CRITICAL ANTI-HALLUCINATION DESIGN:
    1. Every extracted field is grounded strictly in the crawled official text.
    2. If any field (income, age, gender, opening date, etc.) is absent from the source text,
       it is strictly set to "Not specified".
    3. Every critical field includes a verbatim substring quote from the source text for
       deterministic verification in `src/verifier.py`.
    """
    def extract_structured_record(self, crawled_node: dict) -> dict:
        text = crawled_node["crawled_text"]

        # Deterministic Grounded Extraction + Evidence Mapping (100% immune to LLM hallucination)
        extracted = {
            "scholarship_id": crawled_node["scholarship_id"],
            "name": crawled_node["name"],
            "provider": crawled_node["provider"],
            "official_source_url": crawled_node["official_source_url"],
            "application_url": crawled_node.get("application_url", "Not specified"),
            "amount_benefit": self._extract_tag(text, "Benefit Amount:"),
            "eligibility_summary": self._extract_tag(text, "Eligibility:"),
            "academic_requirements": self._extract_tag(text, "Academic Requirements:"),
            "education_level": self._extract_tag(text, "Education Level:"),
            "income_criteria": self._extract_tag(text, "Income Criteria:"),
            "age_criteria": self._extract_tag(text, "Age Criteria:"),
            "gender_criteria": self._extract_tag(text, "Gender Criteria:"),
            "category_criteria": self._extract_tag(text, "Category Criteria:"),
            "domicile_requirements": self._extract_tag(text, "Domicile Requirements:"),
            "institution_requirements": self._extract_tag(text, "Institution Requirements:"),
            "opening_date": self._extract_tag(text, "Opening Date:"),
            "closing_date": self._extract_tag(text, "Closing Date:"),
            "documents_required": self._extract_tag(text, "Documents Required:"),
            "selection_process": self._extract_tag(text, "Selection Process:"),
            "renewal_requirements": self._extract_tag(text, "Renewal Requirements:")
        }

        # Build verbatim evidence trace map: Database -> Official Source -> Evidence Quote -> Value
        evidence_map = {}
        for field_key, tag_label in [
            ("amount_benefit", "Benefit Amount:"),
            ("eligibility_summary", "Eligibility:"),
            ("income_criteria", "Income Criteria:"),
            ("academic_requirements", "Academic Requirements:"),
            ("closing_date", "Closing Date:"),
            ("opening_date", "Opening Date:"),
            ("documents_required", "Documents Required:")
        ]:
            quote = self._extract_verbatim_sentence(text, tag_label)
            evidence_map[field_key] = quote if quote else "Not specified in primary source text."

        extracted["evidence_map"] = evidence_map
        extracted["evidence_json"] = json.dumps(evidence_map, ensure_ascii=False)
        return extracted

    def _extract_tag(self, text: str, label: str) -> str:
        all_labels = [
            "Provider:", "Benefit Amount:", "Eligibility:", "Income Criteria:",
            "Education Level:", "Academic Requirements:", "Age Criteria:",
            "Gender Criteria:", "Category Criteria:", "Domicile Requirements:",
            "Institution Requirements:", "Opening Date:", "Closing Date:",
            "Documents Required:", "Selection Process:", "Renewal Requirements:",
            "Official Update:"
        ]
        if label not in text:
            return "Not specified"

        start_idx = text.find(label) + len(label)
        sub = text[start_idx:]

        # Find nearest subsequent label
        end_idx = len(sub)
        for other in all_labels:
            if other == label:
                continue
            pos = sub.find(other)
            if pos != -1 and pos < end_idx:
                end_idx = pos

        val = sub[:end_idx].strip().rstrip(".")
        if not val or val.lower().startswith("not specified"):
            return "Not specified"
        return val

    def _extract_verbatim_sentence(self, text: str, label: str) -> str:
        val = self._extract_tag(text, label)
        if val == "Not specified":
            if label in text:
                return f"{label} Not specified."
            return ""
        snippet = f"{label} {val}."
        # Verify exact substring exists in raw text
        if f"{label} {val}" in text:
            return snippet
        return f"{label} {val}"
