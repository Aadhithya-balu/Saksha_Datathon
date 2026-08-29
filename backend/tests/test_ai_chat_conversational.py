"""Issue: AI Chat quality & conversational improvements.

Verifies the local fallback generator produces relevant, conversational
answers (direct field lookups, entity profiles, counts, smalltalk) instead of
always dumping a rote record list.
"""
from __future__ import annotations

import asyncio

from app.ai.chat.llm_generator import LLMGenerator


_SAMPLE = """### System Clock
Current date and time: 2026-08-27 10:00 (Thursday)

### Crime Cases
CR-2026-MYS-001 | Category: Theft & Burglaries | Status: Under Investigation | Priority: High | Progress: 40% | District: Mysuru | FIR: FIR-789/MYS/2026
CR-2026-BLR-002 | Category: Cyber Crime | Status: Open | Priority: Medium | Progress: 10% | District: Bengaluru Urban | FIR: FIR-101/BLR/2026

### Criminal Records
Criminal Name: Ramu Swamy | Age: 34 | Status: At Large | Aliases: R. Swamy | Risk Score: HIGH | Linked Cases: 3
Criminal Name: Vikram Yadav | Age: 41 | Status: Incarcerated | Gang: Yadav Gang | Linked Cases: 5
"""

# Reproduces the analytics-engine distribution lines (issue #203) so the answer
# quality fixes can be regression-tested against realistic retrieval context.
_SAMPLE_STATS = """### System Clock
Current date and time: 2026-08-29 10:00 (Saturday)

### Saksha Analytics Engine - Summary
Total crimes: 60, Open cases: 42, Total FIRs: 11, Resolution rate: 30%.

### Saksha Analytics Engine - District Comparison
District Bengaluru Urban has 20 registered crime cases, District Mysuru has 10 registered crime cases, District Dharwad has 8 registered crime cases, District Belagavi has 6 registered crime cases.

### Saksha Analytics Engine - Category Breakdown
Category Cyber Crime accounts for 15 cases, Category Theft & Burglaries accounts for 12 cases, Category Narcotics accounts for 9 cases.

### Saksha Analytics Engine - Recent Activity
System date/time now: 2026-08-29 10:00:00
Period analyzed: 7 days
New crime cases registered: 3
New FIRs filed: 1
Most recent case on file: CR-2026-MYS-001
Most recent FIR on file: FIR-789/MYS/2026

### Saksha PostgreSQL Database - Fir
FIR Number: 2026/104 | Complainant: K. S. Narayanan | Status: Open | Sections: 420/468 IPC | Filed: 2026-08-20 10:00 | Narrative: Cheating and forgery of documents at a Bengaluru bank. | Accused/Suspects: Vikram Yadav

### Saksha PostgreSQL Database - Cases
Case: CR-2026-MYS-001 | Status: Under Investigation | Priority: High | Progress: 40% | Description: Burglary at Mysuru residence. | MO Tags: lock-picking, night-time | Category: Theft & Burglaries | Location: Mysuru, Devaraja | Occurred: 2026-08-01 02:00 | Reported: 2026-08-01 09:00 | Linked FIRs: FIR-789/MYS/2026 | Assigned Officer: Ravi Kumar (IO-3921)

### Saksha PostgreSQL Database - Criminal
Name: Ramu Swamy | Status: At Large | Aliases: R. Swamy | Gender: Male | Address: Hassan | MO: Burglary and theft primarily in residential areas | Marks: birthmark on left hand

### Saksha Neo4j Graph Database - Person Network
Node: Ramu Swamy (Type: Criminal, Risk: 0.8)
Node: Vikram Yadav (Type: Criminal, Risk: 0.9)
Link: Ramu Swamy --[KNOWS]--> Vikram Yadav
"""

# Mimics the live retrieval for a location-scoped list question: only RAG chunks
# (no dedicated Cases section), so the district distribution is the evidence.
_RAG_ONLY = """### Vector Retrieval
Bangalore/Urban has 1 registered crime cases. Mysuru has 14 registered crime cases. Bengaluru Urban has 28 registered crime cases.

### Criminal Records
Criminal Name: Ramu Swamy | Age: 34 | Status: At Large
"""


def _local(message: str, context: str = _SAMPLE) -> str:
    async def _run() -> str:
        out = ""
        async for chunk in LLMGenerator()._generate_local(message, context, "system"):
            out += chunk
        return out

    return asyncio.run(_run())


def test_specific_field_status_answer():
    out = _local("What is the status of case CR-2026-MYS-001?")
    assert "Under Investigation" in out
    assert "CR-2026-MYS-001" in out


def test_entity_profile_for_person():
    out = _local("Tell me about criminal Ramu Swamy")
    assert "Ramu Swamy" in out
    assert "At Large" in out
    assert "Risk Score" in out


def test_case_profile_not_fir():
    out = _local("Show case CR-2026-MYS-001")
    assert "CR-2026-MYS-001" in out
    # Should highlight the case itself, not just its FIR number.
    assert "Theft & Burglaries" in out


def test_count_question_returns_number():
    out = _local("How many cases are there in Bengaluru?")
    assert "**1**" in out


def test_smalltalk_greeting():
    out = _local("hello")
    assert "SAKSHA AI" in out


def test_gratitude_reply():
    out = _local("thanks for the help")
    assert "welcome" in out.lower()


def test_stats_query_is_breakdown_not_single_profile():
    out = _local("Get crime statistics")
    assert "found" in out


def test_empty_db_refusal_still_grounded():
    out = _local("Tell me about criminals in Mysuru", context="### System Clock\nCurrent date and time: 2026-08-27")
    low = out.lower()
    assert ("could not find" in low) or ("no " in low) or ("unavailable" in low)


def test_district_ranking_lists_districts_not_summary():
    out = _local("which district has the highest crime?", context=_SAMPLE_STATS)
    assert "Bengaluru Urban" in out
    assert "highest" in out.lower()
    assert "Total crimes" not in out


def test_district_count_uses_distribution_total():
    out = _local("how many cases are in Bengaluru Urban?", context=_SAMPLE_STATS)
    assert "**20**" in out
    assert "Bengaluru Urban" in out


def test_statistics_synonym_does_not_refuse():
    out = _local("what are the statistics?", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find" not in low
    assert "found" in low


def test_fir_list_excludes_recency_noise():
    out = _local("Show all FIRs", context=_SAMPLE_STATS)
    assert "2026/104" in out
    assert "Most recent" not in out
    assert "System date/time" not in out


def test_case_list_excludes_recency_noise():
    out = _local("list cases", context=_SAMPLE_STATS)
    assert "CR-2026-MYS-001" in out
    assert "New crime cases registered" not in out


def test_show_all_cases_not_refused_when_only_distribution():
    out = _local("Show all cases in Bengaluru Urban", context=_RAG_ONLY)
    low = out.lower()
    assert "could not find" not in low
    assert "Bengaluru Urban" in out


def test_specific_entity_still_refuses_when_kind_absent():
    out = _local("Tell me about officer Ravi Kumar", context=_SAMPLE_STATS)
    low = out.lower()
    assert "officer record" in low
    assert "CR-2026-MYS-001" not in out


def test_criminal_profile_not_buried_under_other_entities():
    out = _local("Tell me about criminal Ramu Swamy", context=_SAMPLE_STATS)
    assert "Here's the profile I found" in out
    assert "Ramu Swamy" in out
    assert "At Large" in out
    assert "CR-2026-MYS-001" not in out


def test_complainant_question_returns_fir_profile():
    out = _local("Who is the complainant in FIR 2026/104?", context=_SAMPLE_STATS)
    assert "K. S. Narayanan" in out
    assert "2026/104" in out


def test_named_person_not_in_records_refuses_honestly():
    out = _local("Aadhi crime records?", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find any records for" in low
    assert "aadhi" in low
    # Must not fall back to the aggregate-statistics keyword dump.
    assert "Total crimes" not in out
    assert "Category" not in out


def test_named_person_not_in_records_refuses_when_lowercased():
    out = _local("aadhi crime records", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find any records for" in low
    assert "Total crimes" not in out


def test_superlative_district_question_not_caught_by_name_gate():
    out = _local("Which district has the most crime cases?", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find any records for" not in low
    assert "Bengaluru Urban" in out


def test_offtopic_question_offers_coverage_not_keyword_dump():
    out = _local("What is the airspeed velocity of an unladen swallow?", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find" in low
    assert "records i have on hand cover" in low
    assert "Total crimes" not in out
    assert "CR-2026-MYS-001" not in out


def test_shows_any_number_of_cases_not_false_person_refusal():
    out = _local("How many cases are in bengaluru urban?", context=_SAMPLE_STATS)
    low = out.lower()
    assert "could not find any records for" not in low
    assert "**20**" in out
