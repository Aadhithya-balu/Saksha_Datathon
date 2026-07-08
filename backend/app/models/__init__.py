"""Import every model so SQLAlchemy's mapper registry is fully populated."""
from app.models.crime_category import (
    Act, CaseCategory, CaseStatusMaster, CrimeHead, CrimeSubHead,
    Court, Designation, GravityOffence, Rank, Section, State,
)
from app.models.location import District, Unit
from app.models.officer import Officer
from app.models.criminal import Accused
from app.models.victim import Victim
from app.models.crime import CaseMaster
from app.models.fir import ActSectionAssociation, ArrestSurrender, ChargesheetDetails, ComplainantDetails
from app.models.role import Role
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.report import Report
from app.models.evidence import Evidence

__all__ = [
    "State", "District", "Unit", "Rank", "Designation",
    "CrimeHead", "CrimeSubHead", "CaseCategory", "CaseStatusMaster",
    "GravityOffence", "Act", "Section", "Court",
    "Officer", "Accused", "Victim", "CaseMaster",
    "ActSectionAssociation", "ArrestSurrender", "ChargesheetDetails", "ComplainantDetails",
    "Role", "User", "AuditLog", "Report", "Evidence",
]
