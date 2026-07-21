from pydantic import BaseModel, ConfigDict, Field


class FutureDistrictRiskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    district: str = Field(..., alias="DISTRICT", min_length=1)
    year: int = Field(..., alias="YEAR", ge=1900, le=2100)
    violent_crime: float = Field(..., alias="VIOLENT_CRIME", ge=0)
    property_crime: float = Field(..., alias="PROPERTY_CRIME", ge=0)
    women_crime: float = Field(..., alias="WOMEN_CRIME", ge=0)
    previous_year_crime: float = Field(..., alias="PREVIOUS_YEAR_CRIME", ge=0)
    crime_growth: float = Field(..., alias="CRIME_GROWTH")
    rolling_avg: float = Field(..., alias="ROLLING_AVG", ge=0)


class FutureDistrictRiskMetrics(BaseModel):
    r2: float
    mae: float
    rmse: float


class FutureDistrictRiskResponse(BaseModel):
    predicted_crime_count: float
    risk_level: str
    model: str
    metrics: FutureDistrictRiskMetrics
