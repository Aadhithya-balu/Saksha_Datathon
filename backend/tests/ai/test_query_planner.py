"""Tests for QueryPlanner — intent/entity to backend-call mapping."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from app.ai.chat.entity_extractor import ExtractedEntities
from app.ai.chat.intent_router import Intent
from app.ai.chat.query_planner import QueryPlanner


class TestCriminalPlanning:
    def test_criminal_intent_with_district_plans_district_search(self):
        """Regression: 'Bengaluru criminal lists' must search criminals by the
        extracted district, not only fetch unfiltered offender dossiers."""
        entities = ExtractedEntities(district="Bengaluru")
        plan = QueryPlanner().plan([Intent.CRIMINAL_HISTORY], entities)
        methods = [call.method for call in plan.backend_calls]
        assert "search_criminals" in methods
        assert "offender_dossiers" in methods

    def test_criminal_intent_without_person_keeps_dossiers_only(self):
        entities = ExtractedEntities()
        plan = QueryPlanner().plan([Intent.CRIMINAL_HISTORY], entities)
        assert [call.method for call in plan.backend_calls] == ["offender_dossiers"]

    def test_criminal_intent_with_person_name_gets_profile_and_network(self):
        entities = ExtractedEntities(person_name="Ramu Swamy")
        plan = QueryPlanner().plan([Intent.CRIMINAL_HISTORY], entities)
        methods = [call.method for call in plan.backend_calls]
        assert "get_criminal" in methods
        assert "get_person_network" in methods
