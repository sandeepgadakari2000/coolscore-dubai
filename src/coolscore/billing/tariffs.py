"""Tariffs loaded from the assumption register (every number sourced there)."""

from __future__ import annotations

from dataclasses import dataclass

from coolscore import config

@dataclass(frozen=True)
class DewaTariff:
    """DEWA residential electricity: progressive slabs plus a per-kWh fuel surcharge."""

    slab_limits: tuple[float, ...]   # upper kWh bound of each slab (inf for the last)
    slab_rates: tuple[float, ...]    # AED per kWh
    fuel_surcharge: float            # AED per kWh


@dataclass(frozen=True)
class DistrictCoolingTariff:
    """District cooling with a capacity (demand) charge (e.g. Empower's published tariff)."""

    consumption: float               # AED per RTh
    capacity_per_rt_year: float      # AED per RT per year
    fuel_surcharge: float            # AED per RTh
    meter_fee_month: float           # AED per month


@dataclass(frozen=True)
class SingleBuildingTariff:
    """Building-level chiller plant billed on consumption only (RSB RD10 caps)."""

    consumption: float               # AED per RTh
    fuel_surcharge: float            # AED per RTh


@dataclass(frozen=True)
class Tariffs:
    dewa: DewaTariff
    district: DistrictCoolingTariff
    single_building: SingleBuildingTariff
    vat: float
    rt_kw: float


def load(meter_fee: str = "central") -> Tariffs:
    """All tariffs from ``config/assumptions.yaml`` (refuses placeholders)."""
    slabs = config.require("billing.dewa.residential_electricity_slabs")
    limits = tuple(float("inf") if s["upto_kwh"] is None else float(s["upto_kwh"]) for s in slabs)
    dc = "billing.district_cooling."
    return Tariffs(
        dewa=DewaTariff(limits, tuple(float(s["aed_per_kwh"]) for s in slabs),
                        float(config.require("billing.dewa.fuel_surcharge"))),
        district=DistrictCoolingTariff(
            consumption=float(config.require(dc + "consumption_charge")),
            capacity_per_rt_year=float(config.require(dc + "capacity_charge")),
            fuel_surcharge=float(config.require(dc + "fuel_surcharge")),
            meter_fee_month=float(config.require(dc + "meter_admin_fee")[meter_fee]),
        ),
        single_building=SingleBuildingTariff(
            consumption=float(config.require(dc + "single_building_consumption_cap")),
            fuel_surcharge=float(config.require(dc + "fuel_surcharge")),
        ),
        vat=float(config.require("billing.vat_rate")),
        rt_kw=float(config.require("constants.rt_to_kw_thermal")),
    )
