from app.ai.chat.intent_router import IntentRouter
from app.ai.chat.entity_extractor import EntityExtractor
from app.ai.chat.query_planner import QueryPlanner

msg = "Tell me about case CR-2026-MYS-001"
ir = IntentRouter()
er = EntityExtractor()
qp = QueryPlanner()

intents = ir.detect(msg)
print("intents:", [i.value for i in intents.intents])
print("scores:", intents.scores)
entities = er.extract(msg)
print("entities.case_id:", entities.case_id)
print("entities.person_name:", entities.person_name)
plan = qp.plan(intents.intents, entities)
print("plan calls:", [(c.service, c.method, c.params) for c in plan.backend_calls])
