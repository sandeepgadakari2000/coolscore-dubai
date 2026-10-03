# Business model

> Every price, volume and cost here is an **assumption** (marked PROPOSAL/PLACEHOLDER in
> `config/assumptions.yaml` → `business`), not market data. The Business Case page recomputes everything live.

## Options

| Option | Who pays | How | For | Against |
|---|---|---|---|---|
| A. Portal API licence | Property portal | Per scored listing per month (assumed AED 1.50) or annual licence | Scale: every listing; the pattern works abroad (a US portal shows energy-cost estimates; UK listings carry EPC cost estimates) | Long sales cycle; needs validation first; portals may build their own |
| B. Brokerage subscription | Brokerages | Per agent seat (assumed AED 149/month, min. 10 seats) + branded unit reports | Brokers feel the "how much is the AC?" question weekly (to test, H5); fast decisions; pilot-able | Smaller tickets; churn if the badge doesn't move enquiries |
| C. Developer design/marketing reports | Developers | Per project (assumed AED 35,000) | High ticket; uses the physics engine directly | Lumpy; needs credibility and relationships |
| D. Consumer freemium | Tenants/buyers | Free score; paid detailed report (assumed AED 29) | Brand and lead generation | A standalone consumer energy-score startup in the US is listed as inactive; low willingness to pay |

## Recommendation: B first, A as the scale channel, C opportunistically, D free

1. **Start with brokerages (B).** It is the shortest path to real-world proof. A 90-day pilot on one brokerage's
   active listings produces exactly what portals and developers will ask for: badge impact on enquiries, real
   bills (brokers can ask landlords) and trust data.
2. **Sell the API to a portal (A) once validated.** One portal deal is worth more than all broker seats combined
   (in the default plan, month 12 portal revenue AED 30,000 vs broker seats about AED 17,000), but only with
   evidence in hand.
3. **Developer reports (C)** are high-margin, credibility-heavy work. Take them when a pilot or interview opens a
   door. Don't plan the company around them.
4. **Keep the consumer score free (D)** as distribution and data collection (opt-in bill sharing).

Why not portal-first: no validation yet, and the hardest objection (Q3 in `interview_prep.md`) is better answered
with pilot data than with a deck.

## Unit economics (defaults)

| Item | Value | Note |
|---|---|---|
| Cost to score a listing | ≈ AED 0.00 | Model lookup in milliseconds |
| AI listing parse (optional) | ≈ AED 0.018 per listing | Claude Haiku 4.5 at USD 1/5 per M tokens × ~2,000 in / 600 out tokens (placeholder token counts) × 3.67 AED/USD |
| Broker seat | AED 149/month vs ≈ AED 7 cost to serve | ≈ 95 % gross margin |
| Portal scored listing | AED 1.50/month vs ≈ AED 0.02 | ≈ 99 % gross margin |
| Real costs | People, sales time, bill-data collection, legal/privacy | Fixed, not per unit |

## 12-month P&L (default plan, AED)

| | Year 1 |
|---|---|
| Revenue | ≈ 353,000 (pilot 15k, broker seats 94k, portal API 90k from month 10, developer reports 140k, consumer 14k) |
| Costs | ≈ 124,000 (founder unpaid; part-time sales from month 4) |
| Profit | ≈ 229,000 |
| Break-even | Month 9 (profit positive in every month from then on) |
| Without developer reports | Profit ≈ 89,000; break-even still month 9, but only just (month-9 profit ≈ AED 1,600). The model stands on seats + portal |

Sensitivities to watch (all on the Business Case page): portal start month, seats per brokerage, churn, and
whether any developer report closes at all.

## What would change the recommendation

- Brokers don't commit to trying it (H6 fails) → lead with investors (chiller-free pricing) or developers.
- A portal launches its own cooling estimate → partner (supply the physics and validation) or focus on developers.
- Dubai mandates energy labels for leases → official partner or data provider, not competitor.
