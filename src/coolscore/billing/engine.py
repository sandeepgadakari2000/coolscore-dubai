"""Turn simulated cooling energy into Dubai bills, by cooling system and who pays.

Systems
-------
``district_cooling``        provider bills capacity (per contracted RT, even at zero use) +
                            consumption + fuel surcharge + meter fee; in-unit fan-coil fans
                            are on the tenant's DEWA bill.
``building_central_plant``  a single-building chiller plant: consumption only (RSB RD10
                            forbids capacity charges), fans on DEWA.
``dewa_split_ac`` /         the unit's own AC on its DEWA meter: electricity = cooling energy
``dewa_central_ac``         / COP, with COP falling in heat (Al Sa'fat T1→T3 ratings), priced
                            at the marginal DEWA slab.

Payers
------
``tenant``                  tenant pays the cooling bill.
``landlord_chiller_free``   landlord pays the cooling bill; tenant still pays fan electricity.
``service_charge``          cooling cost recovered from the owner through service charges
                            (estimated with the same tariff); tenant pays fan electricity.
DEWA-billed AC is always on the occupant's DEWA account, so its payer is the tenant.

VAT is applied exactly once, to each payer's monthly total.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

from coolscore import config
from coolscore.billing import dewa
from coolscore.billing.tariffs import Tariffs, load
from coolscore.physics.rc5r1c import PhysicsResult

SYSTEMS = ("district_cooling", "building_central_plant", "dewa_split_ac", "dewa_central_ac")
PAYERS = ("tenant", "landlord_chiller_free", "service_charge")
EER_TO_COP = 1.0 / 3.412


@dataclass
class BillingParams:
    """Per-unit billing inputs (arrays of length N)."""

    system: np.ndarray            # int index into SYSTEMS
    payer: np.ndarray             # int index into PAYERS
    size_sqft: np.ndarray
    sqft_per_rt: np.ndarray       # contracted-capacity allocation
    installed_factor: np.ndarray  # AC efficiency vs minimum standard
    fan_w_per_kw: np.ndarray
    other_kwh_month: np.ndarray   # non-cooling, non-appliance household electricity


def _pick(rec, mode, rng, n):
    if mode == "central":
        return np.full(n, float(rec["central"]))
    return rng.uniform(rec["low"], rec["high"], n)


def billing_params(system, payer, size_sqft, hidden="central") -> BillingParams:
    """Billing inputs for units; hidden values central or sampled (numpy Generator)."""
    rng = None if isinstance(hidden, str) else hidden
    mode = "central" if rng is None else "sample"
    system = np.array([SYSTEMS.index(s) if isinstance(s, str) else int(s) for s in np.atleast_1d(system)])
    payer = np.array([PAYERS.index(p) if isinstance(p, str) else int(p) for p in np.atleast_1d(payer)])
    n = len(system)
    return BillingParams(
        system=system,
        payer=np.where(system >= SYSTEMS.index("dewa_split_ac"), 0, payer),
        size_sqft=np.broadcast_to(np.asarray(size_sqft, dtype=float), (n,)).copy(),
        sqft_per_rt=_pick(config.require("billing.district_cooling.contracted_capacity_sqft_per_rt"), mode, rng, n),
        installed_factor=_pick(config.require("billing.equipment.installed_efficiency_factor"), mode, rng, n),
        fan_w_per_kw=_pick(config.require("billing.equipment.fcu_fan_power"), mode, rng, n),
        other_kwh_month=_pick(config.require("billing.dewa.other_household_kwh"), mode, rng, n),
    )


@dataclass
class BillResult:
    """Monthly AED (N, 12) per component, before VAT unless named *_total / vat_*."""

    dc_capacity: np.ndarray
    dc_consumption: np.ndarray
    dc_fuel: np.ndarray
    dc_meter: np.ndarray
    plant_consumption: np.ndarray
    plant_fuel: np.ndarray
    dewa_energy: np.ndarray       # marginal slab charge for cooling/fan electricity
    dewa_fuel: np.ndarray
    vat_tenant: np.ndarray
    vat_landlord: np.ndarray
    tenant_total: np.ndarray
    landlord_total: np.ndarray
    cooling_kwh_e: np.ndarray     # electricity for AC or fans (kWh)
    rth: np.ndarray               # thermal ton-hours
    contracted_rt: np.ndarray     # (N,)

    def annual(self, name: str) -> np.ndarray:
        return getattr(self, name).sum(axis=1)

    def subset(self, idx) -> "BillResult":
        return BillResult(**{f.name: getattr(self, f.name)[idx] for f in fields(self)})


def days_in_months(year: int) -> np.ndarray:
    return np.array([31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)


def compute(phys: PhysicsResult, bp: BillingParams, year: int, tariffs: Tariffs | None = None) -> BillResult:
    """Bills for every unit and month."""
    t = tariffs or load()
    n = len(bp.system)
    days = days_in_months(year)[None, :]
    rth = phys.total_kwh / t.rt_kw
    design_rt = phys.design_kw / t.rt_kw
    contracted_rt = np.maximum(bp.size_sqft / bp.sqft_per_rt, design_rt)

    is_dc = (bp.system == SYSTEMS.index("district_cooling"))[:, None]
    is_plant = (bp.system == SYSTEMS.index("building_central_plant"))[:, None]
    is_dewa_ac = (bp.system >= SYSTEMS.index("dewa_split_ac"))[:, None]

    dc_capacity = np.where(is_dc, contracted_rt[:, None] * t.district.capacity_per_rt_year * days / 365.0, 0.0)  # Empower formula
    dc_consumption = np.where(is_dc, rth * t.district.consumption, 0.0)
    dc_fuel = np.where(is_dc, rth * t.district.fuel_surcharge, 0.0)
    dc_meter = np.where(is_dc, t.district.meter_fee_month, 0.0) * np.ones((1, 12))
    plant_consumption = np.where(is_plant, rth * t.single_building.consumption, 0.0)
    plant_fuel = np.where(is_plant, rth * t.single_building.fuel_surcharge, 0.0)

    # Electricity: AC with temperature-dependent COP, or fan-coil fans.
    eer = config.require("billing.equipment.split_ac_min_eer")
    t_ref = config.settings()["physics"]["cop_reference_temp_c"]
    derate_per_k = (eer["t1_35c"] / eer["t3_46c"] - 1.0) / (46.0 - t_ref)
    cop = (eer["t1_35c"] * EER_TO_COP * bp.installed_factor)[:, None]
    ac_kwh = (phys.total_kwh + derate_per_k * phys.load_x_dt_kwhk) / cop
    fan_kwh = bp.fan_w_per_kw[:, None] * (contracted_rt * t.rt_kw)[:, None] * phys.cooling_hours / 1000.0
    cooling_kwh_e = np.where(is_dewa_ac, ac_kwh, fan_kwh)
    base_kwh = phys.appliance_kwh + bp.other_kwh_month[:, None]
    dewa_energy, dewa_fuel = dewa.marginal_charges(base_kwh, cooling_kwh_e, t.dewa)

    provider = dc_capacity + dc_consumption + dc_fuel + dc_meter + plant_consumption + plant_fuel
    tenant_pays_provider = (bp.payer == PAYERS.index("tenant"))[:, None]
    tenant_pre_vat = dewa_energy + dewa_fuel + np.where(tenant_pays_provider, provider, 0.0)
    landlord_pre_vat = np.where(tenant_pays_provider, 0.0, provider)
    vat_tenant = tenant_pre_vat * t.vat
    vat_landlord = landlord_pre_vat * t.vat
    return BillResult(
        dc_capacity=dc_capacity, dc_consumption=dc_consumption, dc_fuel=dc_fuel, dc_meter=dc_meter,
        plant_consumption=plant_consumption, plant_fuel=plant_fuel, dewa_energy=dewa_energy,
        dewa_fuel=dewa_fuel, vat_tenant=vat_tenant, vat_landlord=vat_landlord,
        tenant_total=tenant_pre_vat + vat_tenant, landlord_total=landlord_pre_vat + vat_landlord,
        cooling_kwh_e=cooling_kwh_e, rth=rth, contracted_rt=contracted_rt,
    )


def true_monthly_cost(annual_rent_aed: float, cooling_month_aed: float, other_dewa_month_aed: float = 0.0) -> dict:
    """Rent + cooling + DEWA share (housing fee 5% of rent + other electricity), AED per month."""
    housing = float(config.require("billing.dewa.housing_fee_rate")) * annual_rent_aed / 12.0
    rent = annual_rent_aed / 12.0
    return {"rent": rent, "cooling": cooling_month_aed, "housing_fee": housing,
            "other_dewa": other_dewa_month_aed,
            "total": rent + cooling_month_aed + housing + other_dewa_month_aed}
