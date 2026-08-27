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
