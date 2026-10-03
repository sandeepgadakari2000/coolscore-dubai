# Interview prep: the 12 toughest questions

Honest answers, with the evidence in this repo. Keep each answer under a minute.

**1. "It's simulated, so why should I trust it?"**
Trust it the way you trust a structural model before the building exists: as physics with its uncertainty shown.
Three layers make it trustworthy. (1) The physics is a recognised standard (ISO 13790), checked against a
line-by-line reference implementation and six invariants. (2) The inputs are Dubai's own: airport-corrected
weather, Al Sa'fat envelope limits, published tariffs, each with a source in one register. (3) It never shows one
number. It shows a calibrated P10–P90 range and labels everything "simulated". What I don't claim yet is accuracy
against real bills. That's the next milestone.

**2. "How accurate is it against real bills?"**
Not yet measured, and I say so on the Methodology page. Against the physics it is very accurate (R² 0.996 with all
inputs; 0.94 from listing facts alone, 80 % of cases inside the range). A published rough band agrees for typical
1-bed and 2-bed bills; studios come out a little low and 3-beds a little high, and I report that. The bill kit and
an automatic validation report are built; the brokerage pilot's first deliverable is 45+ real bill-months.

**3. "Why would a portal show a score that makes some listings look worse?"**
Because buyers already discover the cost, just late, and the portal takes the blame. Three design choices make it
palatable: show a *range* framed as "true cost", not a red "E"; give every low score concrete fixes (blinds, AC
temperature, chiller-free pricing); roll out opt-in, then default once data shows better-qualified leads. The UK
precedent is energy-cost estimates on every rental, required by rule. A portal that leads on transparency
differentiates; one that waits for a regulator gets no credit.

**4. "How did you check nobody had built this?"**
A structured search (English, 2026-10-03): calculators, provider tools, guides, portal features, project scores,
sunlight tools, international precedents. Every entry is linked, and I marked what I opened versus only saw in a
snippet (`competitive_landscape.md`). Every Dubai tool needs your RT, ton-hours or AC tonnage, so they work after
move-in. The closest is one calculator's manual "hot-facing" preset. Gaps I name: Arabic sources, app stores, and
in-house portal tools. I ask brokers about those in interviews.

**5. "What's the single biggest driver of a bill?"**
For district cooling it's often not the building's physics. It's the contracted capacity: a fixed charge per RT,
about 46 % of a typical 1-bed's bill in my model. Among physical factors: building era (envelope rules) beats
facing; facing matters (north cheapest), but west vs east is smaller than people think in energy terms. West shows
up in peak load.

**6. "Your model says west is not much worse than east. Isn't that wrong?"**
It surprised me too, and I chose to report it rather than tune it away. West sun does arrive in the hottest hours
(Phase 1 shows +34 % sun during hours above 38 °C). But cooling *energy* mostly sums the gains, and the building's
mass delays east's morning heat into the hot midday. West's penalty appears in the design peak (+2.5 %) and in AC
efficiency on DEWA-billed systems. Real bills will settle it, and the report is set up to.

**7. "Why physics plus ML instead of just ML?"**
There is no public dataset of unit-level cooling bills, so a pure ML model has nothing to learn from. Physics
creates realistic training data for every combination; ML makes it instant and carries the uncertainty; real
bills then calibrate it. When bills arrive, the residual-correction layer is already built.

**8. "What's your PM judgement here: what did you cut?"**
Villas, other emirates, Arabic (until a native-speaker review), room-level comfort, smart-meter integration, and any
portal scraping. I prioritised the honest range and the validation loop over features, because credibility is the
product.

**9. "Who pays, and why would they?"**
Brokerages first: they field the question weekly (my hypothesis H5, being tested) and pay per seat. Then a portal API
once validated. Developer reports are high-ticket but opportunistic. Consumers get it free. The cost to serve is
close to zero, so this is a sales and trust business, not a compute one.

**10. "What happens when tariffs change?"**
Every tariff lives in one file with source and check date. A change means re-billing the cached simulations and
retraining: minutes, not a rebuild. The fuel surcharge changes monthly, and the register says so.

**11. "What are you least sure about?"**
Three things, in order: contracted capacity per unit (secondary sources only); how much outdoor-air humidity
reaches the unit's meter (fresh-air pre-treatment varies by building); and household behaviour (AC temperature,
leaving it on). All three are explicit hidden variables that widen the range, and the bill template captures them.

**12. "What did your user interviews show?"**
The kit (guides, hypotheses with pass/fail thresholds, outreach scripts) was written first, before the product.
[REAL FINDINGS — FILL AFTER INTERVIEWS: counts, which hypotheses passed, two verbatim quotes with codes.]
I won't present findings I don't have.
