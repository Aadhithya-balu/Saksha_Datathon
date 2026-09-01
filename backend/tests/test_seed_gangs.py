"""Integrity checks for the demo gang rosters (issue #53 gang view).

These tests are DB-free: they verify `CRIMINAL_GANG_MAP` only references criminal
profiles that actually exist in the seed manifest, so a typo's roster can never
silently drop out of the Network gang hierarchy.
"""
import pytest

from app.database.seed_db import CRIMINALS, CRIMINAL_GANG_MAP


def test_every_gang_member_exists_in_seed_manifest():
    names = {row[0] for row in CRIMINALS}
    missing = [name for name in CRIMINAL_GANG_MAP if name not in names]
    assert not missing, f"CRIMINAL_GANG_MAP references unknown criminals: {missing}"


def test_every_gang_has_at_least_two_members():
    undersized = [
        (gang, members)
        for gang, members in _gang_rosters().items()
        if len(members) < 2
    ]
    assert not undersized, f"Gangs with fewer than two members: {undersized}"


def test_gang_affiliations_are_nonempty():
    assert CRIMINAL_GANG_MAP, "demo gang roster must not be empty"
    assert all(gang for gang in CRIMINAL_GANG_MAP.values()), "no blank gang names"


def _gang_rosters():
    rosters: dict[str, list[str]] = {}
    for name, gang in CRIMINAL_GANG_MAP.items():
        rosters.setdefault(gang, []).append(name)
    return rosters