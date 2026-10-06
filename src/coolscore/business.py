"""Business case: pricing, unit economics and a 12-month P&L.

All inputs default to ``assumptions.yaml`` → ``business`` (marked PROPOSAL /
PLACEHOLDER there); the Business Case page lets you change every one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from coolscore import config


@dataclass
class BusinessInputs:
    pricing: dict
    plan: dict
    costs: dict
    usd_to_aed: float
    llm_price: dict
    tokens: dict

    @classmethod
    def defaults(cls) -> "BusinessInputs":
        r = config.require
        return cls(pricing=dict(r("business.pricing")), plan=dict(r("business.plan_12m")),
                   costs=dict(r("business.costs_month")), usd_to_aed=float(r("business.usd_to_aed")),
                   llm_price=dict(r("business.llm_price_per_mtok_usd")), tokens=dict(r("business.tokens_per_listing_parse")))


def llm_cost_per_listing_aed(b: BusinessInputs) -> float:
    usd = (b.tokens["input"] * b.llm_price["input"] + b.tokens["output"] * b.llm_price["output"]) / 1e6
    return usd * b.usd_to_aed


def pnl(b: BusinessInputs, months: int = 12) -> pd.DataFrame:
    """Monthly revenue by stream, costs, profit and cumulative cash (AED)."""
    p, pl, c = b.pricing, b.plan, b.costs
    rows = []
    seats = 0.0
    for m in range(1, months + 1):
        pilot = p["pilot_fee_aed"] if m == 1 else 0.0
        if m > pl["pilot_months"]:
            target_brokerages = pl["brokerages_month_4"] + pl["new_brokerages_per_month"] * (m - pl["pilot_months"] - 1)
            new_seats = max(target_brokerages * pl["seats_per_brokerage"] - seats, 0)
            seats = seats * (1 - pl["monthly_churn"]) + new_seats
        brokers = seats * p["broker_seat_aed_month"]
        portal_listings = pl["portal_scored_listings"] if m >= pl["portal_start_month"] else 0
        portal = portal_listings * p["portal_aed_per_scored_listing_month"]
        developer = p["developer_report_aed"] * pl["developer_reports_per_quarter"] if m % 3 == 0 else 0.0
        consumer = pl["consumer_reports_per_month"] * p["consumer_report_aed"]
        revenue = pilot + brokers + portal + developer + consumer
        llm = llm_cost_per_listing_aed(b) * (portal_listings + seats * 20 + pl["consumer_reports_per_month"])
        fixed = sum(v for k, v in c.items() if k != "part_time_sales_aed")
        sales = c["part_time_sales_aed"] if m > pl["pilot_months"] else 0.0
        cost = llm + fixed + sales
        rows.append({"month": m, "pilot": pilot, "broker_seats": brokers, "portal_api": portal,
                     "developer_reports": developer, "consumer_reports": consumer, "revenue": revenue,
                     "ai_cost": llm, "fixed_costs": fixed, "sales_cost": sales, "costs": cost,
                     "profit": revenue - cost, "seats": seats})
    df = pd.DataFrame(rows)
    df["cumulative"] = df["profit"].cumsum()
    return df


def break_even_month(df: pd.DataFrame) -> int | None:
    """First month from which monthly profit stays positive."""
    pos = df["profit"].to_numpy() > 0
    for i in range(len(pos)):
        if pos[i:].all():
            return int(df["month"].iloc[i])
    return None


def unit_economics(b: BusinessInputs) -> dict:
    """Per broker seat and per scored listing."""
    llm = llm_cost_per_listing_aed(b)
    seat_cost = llm * 20 + b.costs["hosting_aed"] / max(b.plan["seats_per_brokerage"] * 5, 1)
    seat_price = b.pricing["broker_seat_aed_month"]
    listing_price = b.pricing["portal_aed_per_scored_listing_month"]
    # a price of 0 has no margin (None), not a division by zero
    return {"llm_cost_per_listing_aed": llm, "broker_seat_price": seat_price, "broker_seat_cost": seat_cost,
            "broker_seat_margin": 1 - seat_cost / seat_price if seat_price > 0 else None,
            "listing_price": listing_price, "listing_margin": 1 - llm / listing_price if listing_price > 0 else None}
