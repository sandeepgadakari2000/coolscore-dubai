"""From listing-level facts to the physical parameters of each simulated unit.

A :class:`ListingSpec` holds what a tenant can learn from a listing or a
viewing (plus optional household details). :func:`build_params` turns specs
into :class:`UnitParams`: one numpy array per physical parameter, one entry
per unit. Facts a listing can't tell us (exact glazing, infiltration,
behaviour...) are *hidden variables*: set to their central values for a single
deterministic run, or sampled from their ranges with a random generator so the
simulated dataset carries realistic uncertainty (Phase 4).

Sources: ``config/archetypes.yaml`` and ``config/assumptions.yaml`` (facts) and
``config/settings.yaml`` → ``physics`` (geometry and behaviour design choices).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Iterable

import numpy as np
import pandas as pd

from coolscore import config
from coolscore.physics import schedules, shading
from coolscore.weather import dataset

SQFT_TO_M2 = 0.09290304
ORIENTATIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
ERA_TO_ARCHETYPE = {"before_2005": "A1", "2005_2014": "A2", "2015_2021": "A3", "2022_plus": "A4"}
AWAY_MODES = ("keep_setpoint", "setback", "off")


@dataclass
class ListingSpec:
    """What a listing (or a viewing) tells us about a unit."""

    community: str
    era_band: str
    size_sqft: float
    bedrooms: int
    floor: int
    total_floors: int
    facing: str                      # "W", or a corner like "W+N"
    glass: str = "medium"            # low / medium / high / floor_to_ceiling
    balcony: str = "none"            # none / small / deep
    obstruction: str = "partial"     # open / partial / heavy
    household_size: int | None = None
    occupancy: str | None = None     # away_daytime / home_daytime
    setpoint_c: float | None = None
    ramadan: bool = False

    def facades(self) -> tuple[int, int]:
        """Orientation indices of the primary and (corner) secondary facade; -1 if none."""
        parts = [p.strip().upper() for p in self.facing.split("+")]
        if len(parts) > 2 or any(p not in ORIENTATIONS for p in parts):
            raise ValueError(f"facing must be one of {ORIENTATIONS} or 'A+B', got {self.facing!r}")
        first = ORIENTATIONS.index(parts[0])
        second = ORIENTATIONS.index(parts[1]) if len(parts) == 2 else -1
        return first, second

    def validate(self) -> None:
        if not 1 <= self.floor <= self.total_floors:
            raise ValueError("floor must be between 1 and total_floors")
        if self.era_band not in ERA_TO_ARCHETYPE:
            raise ValueError(f"unknown era band {self.era_band!r}")
        if self.community not in config.communities()["communities"]:
            raise ValueError(f"unknown community {self.community!r}")
        self.facades()


@dataclass
class UnitParams:
    """Physical and behavioural parameters, one array entry per unit."""

    floor_area_m2: np.ndarray
    orient1: np.ndarray            # int 0-7
    orient2: np.ndarray            # int 0-7, or -1 for a single facade
    len1_m: np.ndarray
    len2_m: np.ndarray
    floor_height_m: np.ndarray
    wwr: np.ndarray
    wall_u: np.ndarray
    roof_u: np.ndarray
    win_u: np.ndarray
    win_shgc: np.ndarray
    top_floor: np.ndarray          # bool
    balcony_depth_m: np.ndarray
    balcony_frac: np.ndarray
    obstruction_deg: np.ndarray
    albedo: np.ndarray
    opaque_absorptance: np.ndarray
    blind_factor: np.ndarray
    am_per_af: np.ndarray
    cm_per_af: np.ndarray
    infiltration_ach: np.ndarray
    untreated_vent_m3s: np.ndarray
    people: np.ndarray
    appliance_wm2: np.ndarray
    profile: np.ndarray            # int, schedules.profile_id
    setpoint_c: np.ndarray
    away_mode: np.ndarray          # int index into AWAY_MODES
    setback_k: np.ndarray
    window_opening: np.ndarray     # bool, ventilates instead of cooling in mild weather
    rh_target: np.ndarray

    @property
    def n(self) -> int:
        return len(self.floor_area_m2)

    def subset(self, idx) -> "UnitParams":
        return UnitParams(**{f.name: getattr(self, f.name)[idx] for f in fields(self)})

    def replace(self, **changes) -> "UnitParams":
        """Copy with some parameters changed (scalars are broadcast)."""
        values = {f.name: np.array(getattr(self, f.name), copy=True) for f in fields(self)}
        for name, v in changes.items():
            values[name] = np.broadcast_to(np.asarray(v), (self.n,)).astype(values[name].dtype).copy()
        return UnitParams(**values)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame({f.name: getattr(self, f.name) for f in fields(self)})

    @classmethod
    def concat(cls, parts: Iterable["UnitParams"]) -> "UnitParams":
        parts = list(parts)
        return cls(**{f.name: np.concatenate([getattr(p, f.name) for p in parts]) for f in fields(cls)})


def _pick(triple_or_range, mode, rng: np.random.Generator | None):
    """Central value, or a uniform draw from low..high."""
    if isinstance(triple_or_range, dict):
        low, central, high = triple_or_range["low"], triple_or_range["central"], triple_or_range["high"]
    else:
        low, central, high = triple_or_range
    if mode == "central":
        return float(central)
    return float(rng.uniform(low, high))


def _glazing(arch_id: str, wwr: float, mode: str, rng) -> tuple[float, float]:
    """(U, SHGC) of the glazing for an archetype and window-to-wall ratio."""
    arch = config.load_yaml("archetypes.yaml")["archetypes"][arch_id]["params"]
    if "glazing_u" in arch:
        return _pick(arch["glazing_u"]["value"], mode, rng), _pick(arch["glazing_shgc"]["value"], mode, rng)
    bands = config.require("glazing_code_limits", "archetypes.yaml")
    band = next(b for b in bands if wwr <= b["wwr_max"] + 1e-9)
    shgc_limit = band["sc"] * config.require("physics.sc_to_shgc")
    compliance = _pick(arch["glazing_compliance"]["value"], mode, rng)
    return float(band["u"]), shgc_limit * compliance


def build_params(specs: Iterable[ListingSpec], hidden: str | np.random.Generator = "central") -> UnitParams:
    """Turn listing specs into unit parameters.

    ``hidden="central"`` uses central values of every hidden variable;
    passing a ``numpy.random.Generator`` samples them instead.
    """
    rng = None if isinstance(hidden, str) else hidden
    mode = "central" if rng is None else "sample"
    ps = config.settings()["physics"]
    arch_all = config.load_yaml("archetypes.yaml")["archetypes"]
    albedo = config.require("physics.ground_albedo")
    absorptance = config.require("physics.opaque_solar_absorptance")
    blinds = config.require("physics.window_shading_reduction")
    mass = config.require("physics.thermal_mass_class")
    infil = config.require("physics.infiltration_ach")
    pretreated = config.require("physics.fresh_air_pretreated_share")
    untreated_frac = config.require("physics.untreated_ventilation_fraction")
    vent = config.require("physics.ashrae_622_ventilation")
    rh = config.require("physics.indoor_humidity_target")
    appl = config.require("physics.appliance_lighting_gain")

    rows: list[dict] = []
    for spec in specs:
        spec.validate()
        arch_id = ERA_TO_ARCHETYPE[spec.era_band]
        arch = arch_all[arch_id]["params"]
        o1, o2 = spec.facades()
        area = spec.size_sqft * SQFT_TO_M2
        fh = _pick(ps["floor_to_floor_m"], mode, rng)
        depth = _pick(ps["unit_depth_m"], mode, rng)
        wwr = _pick(ps["glass_wwr"][spec.glass], mode, rng)
        win_u, shgc = _glazing(arch_id, wwr, mode, rng)
        has_balcony = spec.balcony != "none"
        obst = ps["obstruction"][spec.obstruction]
        z_mid = (spec.floor - 0.5) * fh
        if mode == "central":
            heavy = float(ps["heavy_mass_share"])
            am = (1 - heavy) * mass["medium"]["am_per_af"] + heavy * mass["heavy"]["am_per_af"]
            cm = (1 - heavy) * mass["medium"]["cm_per_af"] + heavy * mass["heavy"]["cm_per_af"]
            untreated_share = (1 - pretreated[spec.era_band]) * untreated_frac["central"]
            people = spec.household_size or spec.bedrooms + 1
            occupancy = spec.occupancy or "away_daytime"
            setpoint = spec.setpoint_c if spec.setpoint_c is not None else ps["setpoint_c"][1]
            away_mode = 0
            window_opening = True
        else:
            cls = "heavy" if rng.random() < ps["heavy_mass_share"] else "medium"
            am, cm = mass[cls]["am_per_af"], mass[cls]["cm_per_af"]
            untreated_share = 0.0 if rng.random() < pretreated[spec.era_band] else _pick(untreated_frac, mode, rng)
            people = spec.household_size or int(rng.integers(1, spec.bedrooms + 3))
            occupancy = spec.occupancy or schedules.OCCUPANCY[int(rng.integers(0, 2))]
            setpoint = spec.setpoint_c if spec.setpoint_c is not None else _pick(ps["setpoint_c"], mode, rng)
            probs = np.array([ps["away_behaviour"][m] for m in AWAY_MODES])
            away_mode = int(rng.choice(len(AWAY_MODES), p=probs / probs.sum()))
            window_opening = bool(rng.random() < ps["window_opening"]["share"])
        q_tot_ls = vent["per_m2_floor_ls"] * area + vent["per_person_ls"] * (spec.bedrooms + 1)
        rows.append({
            "floor_area_m2": area,
            "orient1": o1,
            "orient2": o2,
            "len1_m": area / depth,
            "len2_m": depth * _pick(ps["corner_side_fraction"], mode, rng) if o2 >= 0 else 0.0,
            "floor_height_m": fh,
            "wwr": wwr,
            "wall_u": _pick(arch["wall_u"]["value"], mode, rng),
            "roof_u": _pick(arch["roof_u"]["value"], mode, rng),
            "win_u": win_u,
            "win_shgc": shgc,
            "top_floor": spec.floor == spec.total_floors,
            "balcony_depth_m": _pick(ps["balcony_depth_m"][spec.balcony], mode, rng),
            "balcony_frac": _pick(ps["balcony_width_fraction"], mode, rng) if has_balcony else 0.0,
            "obstruction_deg": float(shading.obstruction_angle_deg(
                _pick(obst["height_m"], mode, rng), _pick(obst["distance_m"], mode, rng), z_mid)),
            "albedo": _pick(albedo, mode, rng),
            "opaque_absorptance": _pick(absorptance, mode, rng),
            "blind_factor": _pick(blinds, mode, rng),
            "am_per_af": am,
            "cm_per_af": cm,
            "infiltration_ach": _pick(infil[spec.era_band], mode, rng),
            "untreated_vent_m3s": untreated_share * q_tot_ls / 1000.0,
            "people": float(people),
            "appliance_wm2": _pick(appl, mode, rng),
            "profile": schedules.profile_id(occupancy, spec.ramadan),
            "setpoint_c": float(setpoint),
            "away_mode": away_mode,
            "setback_k": float(ps["setback_k"]),
            "window_opening": window_opening,
            "rh_target": _pick(rh, mode, rng),
        })
    df = pd.DataFrame(rows)
    int_cols = {"orient1", "orient2", "profile", "away_mode"}
    out = {}
    for f in fields(UnitParams):
        col = df[f.name].to_numpy()
        out[f.name] = col.astype(int) if f.name in int_cols else (
            col.astype(bool) if f.name in {"top_floor", "window_opening"} else col.astype(float))
    return UnitParams(**out)


def weather_site(spec: ListingSpec) -> str:
    """Weather site for a listing's community (coastal merged into central, D8)."""
    return dataset.weather_site_for(spec.community)
