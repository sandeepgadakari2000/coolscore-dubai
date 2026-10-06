"""CoolScore web API for Vercel (one Python function; vercel.json routes /api/* here).

Serves the pages in site/ with the same simulated estimates as the Streamlit app, using the NumPy copy of
the model (no scikit-learn). Locally: ``python tasks.py web`` serves site/ and this API together.
"""


import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from coolscore import web  # noqa: E402

app = FastAPI(title="CoolScore Dubai web API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(GZipMiddleware, minimum_size=800)


class UnitIn(BaseModel):
    listing: dict[str, Any]
    month: int = Field(7, ge=0, le=11)


class WhatIfIn(BaseModel):
    listing: dict[str, Any]
    change: dict[str, Any]


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=6000)


class DirectionIn(BaseModel):
    community: str
    view: str


class CompareIn(BaseModel):
    units: list[dict[str, Any]] = Field(min_length=2, max_length=4)


class InvestorIn(BaseModel):
    listing: dict[str, Any]
    price: float = Field(gt=0)
    rent: float = Field(ge=0)
    service_charge: float = Field(0, ge=0)
    other: float = Field(0, ge=0)


class DeveloperIn(BaseModel):
    community: str = "Business Bay"
    era_band: str = "2022_plus"
    floors: int = Field(24, ge=6, le=40)
    obstruction: str = "partial"
    wwr: float = Field(0.6, ge=0.2, le=0.9)
    shgc: float = Field(0.25, ge=0.15, le=0.6)
    depth: float = Field(0.0, ge=0.0, le=3.0)


def _run(fn, *args):
    try:
        return fn(*args)
    except (ValueError, KeyError) as exc:          # bad listing values: tell the page, don't crash
        raise HTTPException(status_code=422, detail=str(exc).strip("'")) from exc


@app.get("/api/health")
def health() -> dict:
    from coolscore.model import predict

    art = predict.load_artifact()
    return {"status": "ok", "model": "lite" if predict._use_lite() else "full", "scenarios": art["n_scenarios"]}


@app.get("/api/meta")
def meta() -> dict:
    return web.meta()


@app.post("/api/estimate")
def estimate(body: UnitIn) -> dict:
    return _run(web.estimate_payload, body.listing, body.month)


@app.post("/api/heat")
def heat(body: UnitIn) -> dict:
    return _run(web.heat_payload, body.listing, body.month)


@app.post("/api/whatif")
def whatif(body: WhatIfIn) -> dict:
    return _run(web.whatif_payload, body.listing, body.change)


@app.post("/api/parse")
def parse(body: TextIn) -> dict:
    return _run(web.parse_payload, body.text)


@app.post("/api/direction")
def direction(body: DirectionIn) -> dict:
    return _run(web.direction_payload, body.community, body.view)


@app.post("/api/compare")
def compare(body: CompareIn) -> dict:
    return _run(web.compare_payload, body.units)


@app.post("/api/investor")
def investor(body: InvestorIn) -> dict:
    return _run(web.investor_payload, body.listing, body.price, body.rent, body.service_charge, body.other)


@app.post("/api/badge")
def badge(body: UnitIn) -> dict:
    return _run(web.badge_payload, body.listing)


@app.post("/api/developer")
def developer(body: DeveloperIn) -> dict:
    return _run(web.developer_payload, body.community, body.era_band, body.floors, body.obstruction, body.wwr,
                body.shgc, body.depth)


@app.post("/api/business")
def business(body: dict[str, Any]) -> dict:
    return _run(web.business_payload, body)


@app.get("/api/methodology")
def methodology() -> dict:
    return web.methodology_payload()
