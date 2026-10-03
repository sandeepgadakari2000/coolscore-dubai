"""CoolScore B2B API (FastAPI). Run: ``python tasks.py api`` → http://127.0.0.1:8000/docs

Same surrogate as the app; answers are SIMULATED estimates with P10-P90 ranges.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402

from coolscore import __version__, config  # noqa: E402
from coolscore.billing.engine import true_monthly_cost  # noqa: E402
from coolscore.model import predict  # noqa: E402
from coolscore.schemas import (  # noqa: E402
    AedRange, CompareRequest, CompareResponse, Driver, ScoreResponse, UnitRequest,
)

app = FastAPI(
    title="CoolScore Dubai API",
    version=__version__,
    description="Predict a Dubai apartment's cooling cost before you rent or buy it. "
                "Simulated estimates (building physics + Dubai tariffs), not quotes. "
                + config.settings()["app"]["disclaimer"],
)


def _score(unit: UnitRequest) -> ScoreResponse:
    try:
        est = predict.estimate(unit.listing())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    true_cost = None
    if unit.annual_rent_aed:
        true_cost = true_monthly_cost(unit.annual_rent_aed, est.annual.p50 / 12)["total"]
    return ScoreResponse(
        coolscore=est.score,
        cost_intensity_aed_per_sqft_year=round(est.intensity_aed_per_sqft, 3),
        annual_aed=AedRange(**vars(est.annual)),
        summer_month_aed=AedRange(**vars(est.summer_month)),
        winter_month_aed=AedRange(**vars(est.winter_month)),
        true_monthly_cost_aed=true_cost,
        drivers=[Driver(**d) for d in est.drivers],
        landlord_annual_aed_p50=est.landlord_annual_p50,
        formula=est.formula,
        assumed_fields=est.assumed,
        disclaimer=config.settings()["app"]["disclaimer"],
    )


@app.get("/health")
def health() -> dict:
    """Liveness plus whether the model artifact is loadable."""
    try:
        art = predict.load_artifact()
        return {"status": "ok", "model_scenarios": art["n_scenarios"], "simulated": True}
    except FileNotFoundError as exc:
        return {"status": "degraded", "detail": str(exc)}


@app.post("/score", response_model=ScoreResponse)
def score(unit: UnitRequest) -> ScoreResponse:
    """Score one unit: CoolScore A-E, AED ranges, drivers and the formula."""
    return _score(unit)


@app.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    """Score 2-4 units; flags when the cheaper rent is the more expensive home."""
    results = [_score(u) for u in req.units]
    rents = [u.annual_rent_aed for u in req.units]
    cheapest_rent = cheapest_true = None
    flag = False
    if all(r for r in rents):
        cheapest_rent = min(range(len(rents)), key=lambda i: rents[i])
        cheapest_true = min(range(len(results)), key=lambda i: results[i].true_monthly_cost_aed)
        flag = cheapest_rent != cheapest_true
    return CompareResponse(results=results, cheapest_rent_index=cheapest_rent,
                           cheapest_true_cost_index=cheapest_true, cheaper_rent_is_more_expensive_home=flag)
