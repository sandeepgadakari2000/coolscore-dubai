"""Phase 3: billing engine (brief §9 billing checks)."""

from dataclasses import replace

import numpy as np
import pytest

from coolscore.billing import dewa
from coolscore.billing import engine as bill
from coolscore.billing.tariffs import load
from coolscore.physics import engine
from coolscore.physics.params import ListingSpec, build_params
from coolscore.physics.rc5r1c import PhysicsResult

YEAR = 2024
BASE = ListingSpec(community="Business Bay", era_band="2005_2014", size_sqft=800, bedrooms=1,
                   floor=15, total_floors=30, facing="W", glass="medium", balcony="none",
                   obstruction="partial")
COMPONENTS_PRE_VAT = ("dc_capacity", "dc_consumption", "dc_fuel", "dc_meter", "plant_consumption",
                      "plant_fuel", "dewa_energy", "dewa_fuel")


@pytest.fixture(scope="module")
def phys() -> PhysicsResult:
    return engine.run_site_year(build_params([BASE, replace(BASE, facing="N")]), "central", YEAR)


def _zero_physics(n: int = 1) -> PhysicsResult:
    z = np.zeros((n, 12))
    return PhysicsResult(sens_kwh=z, lat_kwh=z, load_x_dt_kwhk=z, cooling_hours=z, appliance_kwh=z,
                         peak_kw=np.zeros(n), design_kw=np.zeros(n))


def _bill(phys, system, payer, n=2):
    return bill.compute(phys, bill.billing_params([system] * n, [payer] * n, [800.0] * n), YEAR)


@pytest.mark.parametrize("system", bill.SYSTEMS)
@pytest.mark.parametrize("payer", bill.PAYERS)
def test_components_sum_to_totals_and_vat_applied_once(phys, system, payer) -> None:
    b = _bill(phys, system, payer)
    vat = load().vat
    pre_vat = sum(getattr(b, c) for c in COMPONENTS_PRE_VAT)
    assert np.allclose((b.tenant_total + b.landlord_total), pre_vat * (1 + vat))
    assert np.allclose(b.vat_tenant + b.vat_landlord, pre_vat * vat)
    assert np.allclose(b.tenant_total, (b.tenant_total - b.vat_tenant) * (1 + vat))


def test_capacity_charge_applies_at_zero_usage() -> None:
    b = bill.compute(_zero_physics(), bill.billing_params(["district_cooling"], ["tenant"], [800.0]), YEAR)
    assert b.annual("dc_consumption")[0] == 0.0
    assert b.annual("dc_capacity")[0] > 0.0
    assert b.annual("tenant_total")[0] > 0.0


def test_capacity_charge_follows_published_formula() -> None:
    t = load()
    bp = bill.billing_params(["district_cooling"], ["tenant"], [6 * 200.0])   # 6 RT at 200 sq ft/RT
    b = bill.compute(_zero_physics(), bp, 2025, t)
    assert b.contracted_rt[0] == pytest.approx(6.0)
    assert b.dc_capacity[0, 0] == pytest.approx(6 * 750 / 365 * 31)            # Empower: per day in month
    assert b.annual("dc_capacity")[0] == pytest.approx(4500.0)


def test_chiller_free_tenant_pays_no_cooling_charges_but_pays_fans(phys) -> None:
    b = _bill(phys, "district_cooling", "landlord_chiller_free")
    tenant_pre_vat = b.tenant_total - b.vat_tenant
    assert np.allclose(tenant_pre_vat, b.dewa_energy + b.dewa_fuel)
    assert (b.annual("dewa_energy") > 0).all()
    assert (b.annual("landlord_total") > b.annual("tenant_total")).all()


def test_single_building_plant_has_no_capacity_charge(phys) -> None:
    b = _bill(phys, "building_central_plant", "tenant")
    assert b.annual("dc_capacity").sum() == 0.0
    assert (b.annual("plant_consumption") > 0).all()


def test_dewa_ac_is_always_on_the_tenant(phys) -> None:
    b = _bill(phys, "dewa_split_ac", "landlord_chiller_free")
    assert b.annual("landlord_total").sum() == 0.0
    assert (b.annual("tenant_total") > 0).all()


def test_dewa_slab_charge_known_values() -> None:
    t = load().dewa
    assert dewa.slab_energy_charge(1000, t) == pytest.approx(230.0)
    assert dewa.slab_energy_charge(2500, t) == pytest.approx(2000 * 0.23 + 500 * 0.28)
    assert dewa.slab_energy_charge(7000, t) == pytest.approx(2000 * 0.23 + 2000 * 0.28 + 2000 * 0.32 + 1000 * 0.38)
    energy, fuel = dewa.marginal_charges(1900, 200, t)
    assert energy == pytest.approx(100 * 0.23 + 100 * 0.28)
    assert fuel == pytest.approx(200 * t.fuel_surcharge)


def test_heat_lowers_ac_efficiency(phys) -> None:
    hot = replace(phys, load_x_dt_kwhk=phys.load_x_dt_kwhk * 2)
    normal = _bill(phys, "dewa_split_ac", "tenant").annual("cooling_kwh_e")
    hotter = _bill(hot, "dewa_split_ac", "tenant").annual("cooling_kwh_e")
    assert (hotter > normal).all()


def test_more_cooling_costs_more(phys) -> None:
    for system in bill.SYSTEMS:
        b = _bill(phys, system, "tenant")
        west, north = b.annual("tenant_total")
        assert west > north, system   # same unit, west uses more energy than north


def test_true_monthly_cost_adds_housing_fee() -> None:
    out = bill.true_monthly_cost(annual_rent_aed=90_000, cooling_month_aed=500)
    assert out["housing_fee"] == pytest.approx(375.0)
    assert out["total"] == pytest.approx(7500 + 500 + 375)
