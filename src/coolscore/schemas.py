"""Request/response schemas shared by the API, the app and the listing parser."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from coolscore import config

Era = Literal["before_2005", "2005_2014", "2015_2021", "2022_plus"]
Glass = Literal["low", "medium", "high", "floor_to_ceiling"]
Balcony = Literal["none", "small", "deep"]
Obstruction = Literal["open", "partial", "heavy"]
System = Literal["district_cooling", "building_central_plant", "dewa_split_ac", "dewa_central_ac"]
Payer = Literal["tenant", "landlord_chiller_free", "service_charge"]
Occupancy = Literal["away_daytime", "home_daytime"]
FACINGS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


class UnitRequest(BaseModel):
    """A unit as described by a listing (optional fields fall back to flagged defaults)."""

    community: str = Field(examples=["Business Bay"])
    size_sqft: float = Field(gt=150, lt=10000, examples=[800])
    bedrooms: int = Field(ge=0, le=6, examples=[1])
    floor: int = Field(ge=1, le=200, examples=[15])
    total_floors: int = Field(ge=1, le=200, examples=[30])
    facing: str = Field(description="N, NE, E, SE, S, SW, W, NW, or a corner like 'W+N'", examples=["W"])
    era_band: Era | None = Field(default=None, examples=["2005_2014"])
    glass: Glass | None = None
    balcony: Balcony | None = None
    obstruction: Obstruction | None = None
    system: System | None = Field(default=None, examples=["district_cooling"])
    payer: Payer | None = Field(default=None, examples=["tenant"])
    annual_rent_aed: float | None = Field(default=None, ge=0, examples=[95000])
    price_aed: float | None = Field(default=None, ge=0)
    household_size: int | None = Field(default=None, ge=1, le=12)
    occupancy: Occupancy | None = None
    setpoint_c: float | None = Field(default=None, ge=18, le=30)

    @model_validator(mode="after")
    def _check(self) -> "UnitRequest":
        parts = [p.strip().upper() for p in self.facing.split("+")]
        if not 1 <= len(parts) <= 2 or any(p not in FACINGS for p in parts):
            raise ValueError("facing must be one of N, NE, E, SE, S, SW, W, NW or 'A+B'")
        self.facing = "+".join(parts)
        if self.floor > self.total_floors:
            raise ValueError("floor cannot exceed total_floors")
        if self.community not in config.communities()["communities"]:
            raise ValueError(f"unknown community; choose one of {sorted(config.communities()['communities'])}")
        return self

    def listing(self) -> dict:
        return self.model_dump(exclude_none=True, exclude={"annual_rent_aed", "price_aed"})


class AedRange(BaseModel):
    p10: float
    p50: float
    p90: float


class Driver(BaseModel):
    driver: str
    aed_per_year: float


class ScoreResponse(BaseModel):
    coolscore: str = Field(description="A (lowest cooling cost per sq ft) to E (highest), standardised")
    cost_intensity_aed_per_sqft_year: float
    annual_aed: AedRange
    summer_month_aed: AedRange
    winter_month_aed: AedRange
    true_monthly_cost_aed: float | None = Field(description="rent + cooling (P50) + housing fee, if rent given")
    drivers: list[Driver]
    landlord_annual_aed_p50: float
    formula: str
    assumed_fields: list[str]
    simulated: bool = True
    disclaimer: str


class CompareRequest(BaseModel):
    units: list[UnitRequest] = Field(min_length=2, max_length=4)


class CompareResponse(BaseModel):
    results: list[ScoreResponse]
    cheapest_rent_index: int | None
    cheapest_true_cost_index: int | None
    cheaper_rent_is_more_expensive_home: bool
