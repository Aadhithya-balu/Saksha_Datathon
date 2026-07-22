"""
API v1 router aggregator.
All module routers are mounted here under settings.API_V1_PREFIX,
giving a clean path for future v2 versioning without touching main.py.
"""
from fastapi import APIRouter

from app.routes import (
    ai_support,
    ai_chat,
    ai_anomaly,
    ai_criminal,
    ai_hotspot,
    ai_risk,
    admin,
    auth,
    crimes,
    criminals,
    dashboard,
    evidence,
    firs,
    investigation,
    locations,
    officers,
    reports,
    users,
    victims,
    crime_cases,
)


api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(crimes.router)
api_router.include_router(firs.router)
api_router.include_router(criminals.router)
api_router.include_router(victims.router)
api_router.include_router(officers.router)
api_router.include_router(evidence.router)
api_router.include_router(locations.router)
api_router.include_router(reports.router)
api_router.include_router(crime_cases.router)
api_router.include_router(investigation.router)
api_router.include_router(ai_support.router)
api_router.include_router(ai_chat.router)
api_router.include_router(ai_anomaly.router)
api_router.include_router(ai_criminal.router)
api_router.include_router(ai_hotspot.router)
api_router.include_router(ai_risk.router)

