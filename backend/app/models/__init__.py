"""
Import every model here so SQLAlchemy's mapper registry is fully populated
before Base.metadata.create_all() or Alembic autogenerate runs.
"""
from app.models.role import Role
from app.models.user import User
from app.models.location import Location
from app.models.crime_category import CrimeCategory
from app.models.officer import Officer
from app.models.criminal import Criminal
from app.models.victim import Victim
from app.models.crime import CrimeCase
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.evidence import Evidence
from app.models.evidence_metadata import EvidenceMetadata
from app.models.evidence_timeline import EvidenceTimeline
from app.models.evidence_assignment import EvidenceAssignment
from app.models.chain_of_custody import ChainOfCustody
from app.models.evidence_ai_summary import EvidenceAISummary
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.models.notification import Notification

__all__ = [
    "Role", "User", "Location", "CrimeCategory", "Officer", "Criminal",
    "Victim", "CrimeCase", "FIR", "FIRCriminalLink", "FIRVictimLink",
    "Evidence", "EvidenceMetadata", "EvidenceTimeline", "EvidenceAssignment",
    "ChainOfCustody", "EvidenceAISummary", "Report", "AuditLog",
    "Notification",
]
