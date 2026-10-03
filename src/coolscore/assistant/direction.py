"""Direction helper: suggest a likely facing from a listing's view description.

Uses map geometry only (bearing from the community centre to the landmark, or
the open-sea side for coastal communities). Always a *suggestion* for the user
to confirm; returns None when there is no reliable answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from coolscore import config

VIEW_PHRASES = ["sea view", "Burj Khalifa view", "Palm view", "Burj Al Arab view", "Ain Dubai view",
                "Dubai Frame view", "canal/lake/golf/community view"]
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


@dataclass
class Suggestion:
    facing: str
    reason: str


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2 (degrees from north)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance (km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


MIN_DISTANCE_KM = 1.0   # closer than this, a "view" can be from almost any side


def to_compass(deg: float) -> str:
    return COMPASS[int((deg + 22.5) // 45) % 8]


def suggest(community: str, view: str) -> Suggestion | None:
    geo = config.load_yaml("landmarks.yaml")
    v = view.lower()
    if "sea" in v:
        side = geo["sea_direction"].get(community)
        return Suggestion(side, "the open sea lies to the north-west of this part of the coast") if side else None
    for name, mark in geo["landmarks"].items():
        lat, lon = mark["at"]
        if any(word in v for word in mark["match"]):
            centre = geo["centres"].get(community)
            if centre is None or distance_km(centre[0], centre[1], lat, lon) < MIN_DISTANCE_KM:
                return None
            b = bearing_deg(centre[0], centre[1], lat, lon)
            return Suggestion(to_compass(b), f"{name.title()} lies to the {to_compass(b)} of {community}")
    return None
