# Real-bill validation report

*Generated 2026-10-03T04:36:46+00:00 by `python tasks.py validate` (also run by the app).*

**Status: no real bills yet.** Real-world accuracy is **not yet validated**. Add anonymised figures to `data/real_bills/` (see its README) and re-run; this report updates automatically.

## Sanity check against a published rough band

Simulated typical district-cooling bills (tenant pays, median month) vs an independent guide's ranges (`assumptions.yaml` → `sanity_bands`; rough, unverified):

| Bedrooms | Simulated median AED/month | Published band | Inside? |
|---|---|---|---|
| Studio | 324 | 350–450 | no |
| 1 | 534 | 450–600 | yes |
| 2 | 826 | 650–850 | yes |
| 3 | 1,218 | 900–1,200 | no |
