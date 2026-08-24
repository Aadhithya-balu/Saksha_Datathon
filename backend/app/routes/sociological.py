"""Sociological Insights routes — demographic, geographic, and socio-economic crime analysis."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services import sociological_service

router = APIRouter(prefix="/sociological", tags=["Sociological Insights"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/dataset-info")
def socioeconomic_dataset_info(current_user: User = Depends(get_current_user)):
    """Provenance of the versioned socio-economic dataset backing this module."""
    from app.services.sociological_service import dataset_info

    return dataset_info()


@router.get("/demographics")
def get_demographics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crime distribution by victim age groups and gender demographics."""
    return sociological_service.get_demographic_analysis(db)


@router.get("/urban-rural")
def get_urban_rural(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crime distribution by urban vs rural classification with population density."""
    return sociological_service.get_urban_rural_analysis(db)


@router.get("/socioeconomic")
def get_socioeconomic(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crime correlation with socio-economic indicators by district."""
    return sociological_service.get_socioeconomic_overlay(db)


@router.get("/population-correlation")
def get_population_correlation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crime rate vs population density scatter data."""
    return sociological_service.get_population_crime_correlation(db)


@router.get("/temporal-demographics")
def get_temporal_demographics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crime by hour of day, day of week, and monthly patterns."""
    return sociological_service.get_temporal_demographic_analysis(db)


@router.get("/offender-demographics")
def get_offender_demographics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Criminal offender demographic analysis (age, gender, status)."""
    return sociological_service.get_offender_demographics(db)
