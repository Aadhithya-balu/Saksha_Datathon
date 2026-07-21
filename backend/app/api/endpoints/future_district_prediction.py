from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.services.future_district_prediction_service import (
    FutureDistrictModelMissingError,
    FutureDistrictPredictionError,
    get_trained_districts,
    predict_future_district_risk,
)
from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.models.user import User
from app.schemas.future_district_prediction import (
    FutureDistrictRiskRequest,
    FutureDistrictRiskResponse,
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/future-district-risk/districts",
    response_model=list[str],
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)
def get_future_district_risk_districts(current_user: User = Depends(get_current_user)):
    try:
        return get_trained_districts()
    except FutureDistrictModelMissingError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except FutureDistrictPredictionError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected future district risk districts error",
        ) from exc


@router.post(
    "/future-district-risk",
    response_model=FutureDistrictRiskResponse,
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)
def predict_future_district_risk_endpoint(
    payload: FutureDistrictRiskRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return predict_future_district_risk(payload)
    except FutureDistrictModelMissingError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except FutureDistrictPredictionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected future district risk prediction error",
        ) from exc
