"""Feature encoding shared by training, the app and the API.

Only facts a person can get from a listing (plus optional household details)
are features. Everything else (exact glazing, infiltration, behaviour...)
stays hidden, so the P10-P90 range reflects real uncertainty.
"""

from __future__ import annotations

import pandas as pd

from coolscore.billing.engine import PAYERS, SYSTEMS
from coolscore.physics.params import ORIENTATIONS

ERAS = ("before_2005", "2005_2014", "2015_2021", "2022_plus")
GLASS = ("low", "medium", "high", "floor_to_ceiling")
BALCONY = ("none", "small", "deep")
OBSTRUCTION = ("open", "partial", "heavy")
SITES = ("central", "inland")
NO_SECOND_FACADE = 8

LISTING_FEATURES = [
    "weather_site", "era", "size_sqft", "bedrooms", "floor", "total_floors", "floor_frac", "top_floor",
    "facing1", "facing2", "corner", "glass", "balcony", "obstruction", "system", "payer",
]
DETAIL_FEATURES = ["household_size", "home_daytime", "setpoint_c"]
CATEGORICAL = ["weather_site", "facing1", "facing2", "system", "payer"]
VARIANTS = {"listing": LISTING_FEATURES, "detailed": LISTING_FEATURES + DETAIL_FEATURES}


def _facings(facing: str) -> tuple[int, int]:
    parts = [p.strip().upper() for p in str(facing).split("+")]
    first = ORIENTATIONS.index(parts[0])
    second = ORIENTATIONS.index(parts[1]) if len(parts) > 1 else NO_SECOND_FACADE
    return first, second


def encode(df: pd.DataFrame) -> pd.DataFrame:
    """Numeric feature table from scenario/listing columns (unknown details may be NaN)."""
    f1, f2 = zip(*[_facings(f) for f in df["facing"]])
    out = pd.DataFrame(index=df.index)
    out["weather_site"] = df["weather_site"].map(SITES.index)
    out["era"] = df["era_band"].map(ERAS.index)
    out["size_sqft"] = df["size_sqft"].astype(float)
    out["bedrooms"] = df["bedrooms"].astype(int)
    out["floor"] = df["floor"].astype(int)
    out["total_floors"] = df["total_floors"].astype(int)
    out["floor_frac"] = out["floor"] / out["total_floors"]
    out["top_floor"] = (out["floor"] == out["total_floors"]).astype(int)
    out["facing1"] = list(f1)
    out["facing2"] = list(f2)
    out["corner"] = (out["facing2"] != NO_SECOND_FACADE).astype(int)
    out["glass"] = df["glass"].map(GLASS.index)
    out["balcony"] = df["balcony"].map(BALCONY.index)
    out["obstruction"] = df["obstruction"].map(OBSTRUCTION.index)
    out["system"] = df["system"].map(SYSTEMS.index)
    out["payer"] = df["payer"].map(PAYERS.index)
    if "household_size" in df:
        out["household_size"] = df["household_size"].astype(float)
        out["home_daytime"] = (df["occupancy"] == "home_daytime").astype(float).where(df["occupancy"].notna())
        out["setpoint_c"] = df["setpoint_c"].astype(float)
    return out
