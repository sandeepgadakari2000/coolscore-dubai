"""Data for the static landing page (``site/``): one fictional tower, scored unit by unit.

The landing film follows one August day around Meridian Heights (the fictional tower of the
Developer View) and stops at four flats: sunrise on an east flat, early afternoon under the
roof, late afternoon on a west flat, night on a north flat. Every number the page shows comes
from here, so the page itself never makes one up:

* every floor x facing scored by the same surrogate as Check a Unit (CoolScore, P10-P90 AED);
* each featured flat's August heat budget (``physics.breakdown``) and its average August day
  of cooling load from the hourly engine;
* the measured typical August day (``data/demo/climate_monthly.json``).

Run: ``python tasks.py landing`` → ``site/data/tower.json``; ``python tasks.py site`` serves ``site/`` on
http://127.0.0.1:5230 (no caching, so edits show on reload). SIMULATED estimates throughout.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import sys
from datetime import date

import numpy as np

from coolscore import config
from coolscore.model import predict
from coolscore.physics import breakdown, rc5r1c
from coolscore.physics.params import ORIENTATIONS, ListingSpec, build_params, weather_site
from coolscore.weather import climate

MONTH = 7  # August (0-based), the hottest month on the bill
TOWER = {
    "name": "Meridian Heights", "community": "Business Bay", "total_floors": 24, "size_sqft": 850,
    "bedrooms": 1, "era_band": "2005_2014", "glass": "high", "balcony": "none", "obstruction": "partial",
    "system": "district_cooling", "payer": "tenant",
}
# The four stops of the film: time of day (local hour), floor and facing.
FEATURED = [
    {"key": "sunrise", "hour": 7, "floor": 17, "facing": "E"},
    {"key": "afternoon", "hour": 13, "floor": 24, "facing": "S"},
    {"key": "evening", "hour": 17, "floor": 14, "facing": "W"},
    {"key": "night", "hour": 22, "floor": 3, "facing": "N"},
]


def _listing(floor: int, facing: str) -> dict:
    return {k: v for k, v in TOWER.items() if k != "name"} | {"floor": floor, "facing": facing}


def _spec(floor: int, facing: str) -> ListingSpec:
    t = TOWER
    return ListingSpec(community=t["community"], era_band=t["era_band"], size_sqft=t["size_sqft"],
                       bedrooms=t["bedrooms"], floor=floor, total_floors=t["total_floors"], facing=facing,
                       glass=t["glass"], balcony=t["balcony"], obstruction=t["obstruction"])


def _unit(est: predict.Estimate) -> dict:
    a = est.annual
    return {
        "floor": est.listing["floor"], "facing": est.listing["facing"], "score": est.score,
        "annual": [round(a.p10), round(a.p50), round(a.p90)],
        "august": round(est.monthly_p50[MONTH]),
        "capacity": round(est.capacity_aed_per_year or 0),   # fixed charge, paid even with the AC off
        "drivers": [[d["driver"], round(d["aed_per_year"])] for d in est.drivers[:3]],
    }


def _august_day(specs: list[ListingSpec]) -> list[list[float]]:
    """Average August day of cooling load (sensible + latent, kW) per unit, by local hour."""
    weather, facades = breakdown._month_window(weather_site(specs[0]), breakdown.YEAR, MONTH)
    res = rc5r1c.simulate(build_params(specs, "central"), weather, facades, keep_hourly=True)
    load_kw = (-res.hourly["phi_hc"] + res.hourly["q_lat"]) / 1000
    in_month = np.asarray(weather.index.month == MONTH + 1)
    hours = np.asarray(weather.index.hour)
    return [[round(float(load_kw[u, in_month & (hours == h)].mean()), 2) for h in range(24)]
            for u in range(len(specs))]


def build() -> dict:
    rows = [_listing(f, o) for f in range(1, TOWER["total_floors"] + 1) for o in ORIENTATIONS]
    units = [_unit(e) for e in predict.estimate_many(rows)]
    by_key = {(u["floor"], u["facing"]): u for u in units}

    specs = [_spec(s["floor"], s["facing"]) for s in FEATURED]
    days = _august_day(specs)
    featured = []
    for stop, spec, day in zip(FEATURED, specs, days):
        hb = breakdown.heat_budget(spec, MONTH)
        total = sum(hb["kwh"].values()) or 1.0
        featured.append(stop | {
            "unit": by_key[(stop["floor"], stop["facing"])],
            "budget_pct": {k: round(100 * v / total) for k, v in hb["kwh"].items()},
            "humidity_pct": round(100 * hb["latent_share"]),
            "load_kw_by_hour": day,
        })

    aug = climate.load()["sites"]["central"][MONTH]
    art = predict.load_artifact()
    p50 = [u["annual"][1] for u in units]
    lo, hi = units[int(np.argmin(p50))], units[int(np.argmax(p50))]
    data = {
        "generated": date.today().isoformat(),
        "simulated_label": config.settings()["app"]["simulated_label"],
        "disclaimer": config.settings()["app"]["disclaimer"],
        "tower": TOWER | {"fictional": True},
        "labels": breakdown.LABELS,
        "score_letters": art["score_letters"],
        "units": units,
        "featured": featured,
        "spread": {"lowest": lo, "highest": hi, "grades": sorted({u["score"] for u in units})},
        "climate": {"month": aug["month"], "tmax": aug["tmax"], "tmin": aug["tmin"],
                    "days_over_40": aug["days_over_40"], "facade_kwh_day": aug["facade_kwh_day"],
                    "hourly": aug["hourly"], "source": climate.load()["source"]},
    }
    out = config.ROOT / "site" / "data" / "tower.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


def serve(port: int = 5230) -> None:
    """Serve the static site locally without caching, with HTTP Range support (browsers need it to seek
    inside the scroll-scrubbed videos; static hosts like Cloudflare Pages or Vercel already do this)."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Accept-Ranges", "bytes")
            super().end_headers()

        def send_head(self):
            rng = self.headers.get("Range", "")
            path = self.translate_path(self.path)
            if not rng.startswith("bytes=") or not os.path.isfile(path):
                return super().send_head()
            size = os.path.getsize(path)
            first, _, last = rng[6:].split(",")[0].partition("-")
            start = int(first) if first else max(0, size - int(last))
            end = min(size - 1, int(last)) if first and last else size - 1
            if start >= size:
                self.send_error(416)
                return None
            f = open(path, "rb")
            f.seek(start)
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            self._remaining = end - start + 1
            return f

        def copyfile(self, source, outputfile) -> None:
            remaining = getattr(self, "_remaining", None)
            if remaining is None:
                return super().copyfile(source, outputfile)
            self._remaining = None
            while remaining > 0:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)

    handler = functools.partial(Handler, directory=str(config.ROOT / "site"))
    print(f"CoolScore landing on http://127.0.0.1:{port}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    if sys.argv[1:2] == ["serve"]:
        serve()
        raise SystemExit
    d = build()
    s = d["spread"]
    print(f"wrote site/data/tower.json: {len(d['units'])} units, grades {''.join(s['grades'])}, "
          f"P50 AED {s['lowest']['annual'][1]:,}–{s['highest']['annual'][1]:,}/yr")
    for f in d["featured"]:
        peak = max(range(24), key=lambda h: f["load_kw_by_hour"][h])
        print(f"  {f['key']:9} floor {f['floor']:2} {f['facing']:2} {f['unit']['score']} "
              f"AED {f['unit']['annual']}  budget {f['budget_pct']}  humidity {f['humidity_pct']}%  "
              f"load@{f['hour']}h {f['load_kw_by_hour'][f['hour']]} kW, peak {peak}h")
