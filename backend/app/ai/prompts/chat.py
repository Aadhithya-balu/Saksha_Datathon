from __future__ import annotations

from typing import Iterable


def build_summary_prompt(question: str, evidence: Iterable[str]) -> str:
    evidence_lines = [f"- {item}" for item in evidence]
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No supporting records found."
    return (
        "Summarize the investigation context using the retrieved records.\n"
        f"Query: {question}\n"
        f"Evidence:\n{evidence_block}"
    )


def build_answer_prompt(question: str, summary: str, evidence: Iterable[str]) -> str:
    evidence_lines = [f"- {item}" for item in evidence]
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No direct evidence found."
    return (
        f"{build_multilingual_answer_prompt()}\n\n"
        "Answer the investigator clearly and concisely using only the supplied context.\n"
        f"Query: {question}\n"
        f"Context summary: {summary}\n"
        f"Evidence:\n{evidence_block}"
    )


def build_multilingual_answer_prompt() -> str:
    """Return system instructions for multilingual-aware response generation."""
    return (
        "You are SAKSHA, an AI crime intelligence assistant for the Karnataka State Police.\n"
        "LANGUAGE RULES:\n"
        "- Detect the language of each user message independently.\n"
        "- Understand the query semantically regardless of the input language.\n"
        "- Respond in the same language the user wrote in (English, Kannada, Kanglish, Hindi, Tamil, Telugu, Malayalam, etc.).\n"
        "- If the user writes in Kanglish (Kannada words in Roman script), respond in Kanglish.\n"
        "- If the user writes in Kannada script, respond in Kannada.\n"
        "- If the user writes in English, respond in English.\n"
        "- Preserve all FIR numbers, case IDs, names, phone numbers, vehicle numbers, and identifiers exactly as they appear in the database.\n"
        "- Never fabricate translations, records, or intelligence.\n"
        "- Never invent data that does not exist in the database.\n"
        "- When searching, map multilingual terms to SAKSHA internal entity names:\n"
        "  * 'tanike' / 'ತನಿಖೆ' / 'investigation' -> investigation\n"
        "  * 'shankita' / 'ಶಂಕಿತ' / 'suspect' / 'criminal' -> suspect/criminal\n"
        "  * 'saakshya' / 'ಸಾಕ್ಷ್ಯ' / 'evidence' -> evidence\n"
        "  * 'aparadha' / 'ಅಪರಾಧ' / 'crime' -> crime\n"
        "  * 'prakarana' / 'ಪ್ರಕರಣ' / 'case' -> case\n"
        "  * 'guptachara' / 'ಗುಪ್ತಚರ' / 'intelligence' -> intelligence\n"
        "  * 'huduku' / 'ಹುಡುಕು' / 'search' -> search\n"
        "  * 'adhikari' / 'ಅಧಿಕಾರಿ' / 'officer' -> officer\n"
        "  * 'badhita' / 'ಬಾಧಿತ' / 'victim' -> victim\n"
        "  * 'nirbandha' / 'ಬಂಧನ' / 'arrest' -> arrest\n"
        "  * 'varadhi' / 'ವರದಿ' / 'report' -> report\n"
        "  * 'jaala' / 'ಜಾಲ' / 'network' -> network\n"
        "  * 'apaya' / 'ಅಪಾಯ' / 'risk' -> risk\n"
        "  - Handle reasonable spelling variations and transliteration differences.\n"
        "  - All queries go through the same authentication, RBAC, and data access rules.\n"
        "  - If the user's language is uncertain, default to the language they used.\n"
    )
