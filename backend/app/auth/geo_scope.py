"""
Geographic Access Scope — centralized enforcement of district/station isolation.

Architecture
------------
Crime records are geographically anchored through:
    CrimeCase → location_id → Location.district / Location.station

Criminals and Victims have no direct district column; they are scoped
transitively via:
    Criminal/Victim → FIRCriminalLink/FIRVictimLink → FIR → CrimeCase → Location

Role policy
-----------
Unrestricted (state-wide):  admin, crime_analyst
Geographically scoped:      investigator, inspector, forensic, policymaker, viewer

A scoped user with district=None or station=None is treated as having NO
permitted scope — they see nothing rather than everything. This prevents
accidental data exposure from incomplete user profiles.

Usage
-----
    from app.auth.geo_scope import GeoScope, get_geo_scope

    # In a route:
    scope: GeoScope = Depends(get_geo_scope)
    query = scope.apply_to_cases(db.query(CrimeCase))

    # Guard a single record:
    scope.check_location(location)   # raises ForbiddenException if out of scope
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Query, Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_CRIME_ANALYST
from app.core.exceptions import ForbiddenException
from app.models.user import User

# Roles that bypass geographic filtering and see all records state-wide.
_UNRESTRICTED_ROLES = {ROLE_ADMIN, ROLE_CRIME_ANALYST}


class GeoScope:
    """Encapsulates the geographic access scope for a single authenticated user.

    Attributes
    ----------
    is_unrestricted : bool
        True for admin / crime_analyst — no geographic filter is applied.
    district : str | None
        The user's permitted district (None means no scope → empty result set).
    station : str | None
        The user's permitted station (None means district-level access only).
    """

    def __init__(self, user: User) -> None:
        self._user = user
        role = getattr(user, "role", None)
        role_name = getattr(role, "name", role if isinstance(role, str) else None)
        self.is_unrestricted: bool = role_name in _UNRESTRICTED_ROLES
        self.district: str | None = user.district if not self.is_unrestricted else None
        self.station: str | None = user.station if not self.is_unrestricted else None

    # ------------------------------------------------------------------
    # Query-level helpers (apply to SQLAlchemy Query objects)
    # ------------------------------------------------------------------

    def apply_to_cases(self, query: Query, *, location_joined: bool = False) -> Query:
        """Filter a CrimeCase query to the user's geographic scope.

        Joins Location if not already joined. Returns an empty-result query
        when the user has no district assigned.
        """
        if self.is_unrestricted:
            return query

        if self.district is None:
            # No district → return nothing safely.
            return query.filter(False)

        from app.models.crime import CrimeCase
        from app.models.location import Location

        if not location_joined:
            query = query.join(Location, CrimeCase.location_id == Location.id)

        query = query.filter(Location.district == self.district)

        if self.station is not None:
            query = query.filter(Location.station == self.station)

        return query

    def apply_to_firs(self, query: Query) -> Query:
        """Filter a FIR query to the user's geographic scope via CrimeCase→Location."""
        if self.is_unrestricted:
            return query

        if self.district is None:
            return query.filter(False)

        from app.models.crime import CrimeCase
        from app.models.fir import FIR
        from app.models.location import Location

        query = (
            query
            .join(CrimeCase, FIR.crime_case_id == CrimeCase.id)
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == self.district)
        )

        if self.station is not None:
            query = query.filter(Location.station == self.station)

        return query

    def apply_to_criminals(self, query: Query, db: Session) -> Query:
        """Filter a Criminal query to the user's geographic scope.

        Criminals are scoped via: Criminal → FIRCriminalLink → FIR → CrimeCase → Location.
        Returns only criminals who have at least one FIR in the user's scope.
        """
        if self.is_unrestricted:
            return query

        if self.district is None:
            return query.filter(False)

        from app.models.crime import CrimeCase
        from app.models.criminal import Criminal
        from app.models.fir import FIR, FIRCriminalLink
        from app.models.location import Location

        scoped_criminal_ids = (
            db.query(FIRCriminalLink.criminal_id)
            .join(FIR, FIRCriminalLink.fir_id == FIR.id)
            .join(CrimeCase, FIR.crime_case_id == CrimeCase.id)
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == self.district)
        )
        if self.station is not None:
            scoped_criminal_ids = scoped_criminal_ids.filter(Location.station == self.station)

        return query.filter(Criminal.id.in_(scoped_criminal_ids.subquery()))

    def apply_to_victims(self, query: Query, db: Session) -> Query:
        """Filter a Victim query to the user's geographic scope.

        Victims are scoped via: Victim → FIRVictimLink → FIR → CrimeCase → Location.
        """
        if self.is_unrestricted:
            return query

        if self.district is None:
            return query.filter(False)

        from app.models.crime import CrimeCase
        from app.models.fir import FIR, FIRVictimLink
        from app.models.location import Location
        from app.models.victim import Victim

        scoped_victim_ids = (
            db.query(FIRVictimLink.victim_id)
            .join(FIR, FIRVictimLink.fir_id == FIR.id)
            .join(CrimeCase, FIR.crime_case_id == CrimeCase.id)
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == self.district)
        )
        if self.station is not None:
            scoped_victim_ids = scoped_victim_ids.filter(Location.station == self.station)

        return query.filter(Victim.id.in_(scoped_victim_ids.subquery()))

    def permitted_fir_ids(self, db: Session) -> set:
        """Return the set of FIR ids visible to this user (used by network service)."""
        if self.is_unrestricted:
            return None  # None signals "no restriction" to callers

        if self.district is None:
            return set()

        from app.models.crime import CrimeCase
        from app.models.fir import FIR
        from app.models.location import Location

        q = (
            db.query(FIR.id)
            .join(CrimeCase, FIR.crime_case_id == CrimeCase.id)
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == self.district)
        )
        if self.station is not None:
            q = q.filter(Location.station == self.station)

        return {row[0] for row in q.all()}

    # ------------------------------------------------------------------
    # Record-level guard (use after fetching a single record by ID)
    # ------------------------------------------------------------------

    def check_location(self, location) -> None:
        """Raise ForbiddenException if *location* is outside the user's scope.

        Pass the Location ORM object associated with the record being accessed.
        A None location is treated as out-of-scope for scoped users.
        """
        if self.is_unrestricted:
            return

        if location is None or self.district is None:
            raise ForbiddenException("Access denied: record is outside your geographic scope")

        if location.district != self.district:
            raise ForbiddenException("Access denied: record is outside your geographic scope")

        if self.station is not None and location.station != self.station:
            raise ForbiddenException("Access denied: record is outside your geographic scope")

    def clamp_district_filter(self, requested_district: str | None) -> str | None:
        """Prevent a scoped user from widening their district filter.

        If the user supplies a district filter that differs from their own,
        their own district takes precedence. Unrestricted users may filter
        freely.
        """
        if self.is_unrestricted:
            return requested_district
        return self.district  # always override with the user's own district

    def clamp_station_filter(self, requested_station: str | None) -> str | None:
        """Prevent a scoped user from widening their station filter."""
        if self.is_unrestricted:
            return requested_station
        return self.station  # always override with the user's own station


def get_geo_scope(current_user: User = Depends(get_current_user)) -> GeoScope:
    """FastAPI dependency — resolves the geographic scope for the current user."""
    return GeoScope(current_user)
