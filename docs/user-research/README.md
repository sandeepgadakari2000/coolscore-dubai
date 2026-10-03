# User-research kit

Use this kit to find out whether the problem is real before the product is finished.
Everything here is a template. **No quote, bill or finding in this folder is real until you add it after a real conversation.**

## What's in the kit

| File | Use it for |
|---|---|
| [hypotheses.md](hypotheses.md) | The beliefs we are testing, with pass/fail thresholds set *before* the interviews |
| [interview_guide_tenants.md](interview_guide_tenants.md) | 25-minute discovery interview with people who rented in Dubai in the last 2 years |
| [interview_guide_brokers.md](interview_guide_brokers.md) | 20-minute interview with leasing/sales agents |
| [interview_guide_investors.md](interview_guide_investors.md) | 25-minute interview with landlords and buy-to-let investors |
| [interview_guide_developers.md](interview_guide_developers.md) | 30-minute interview with developer product, design, sustainability or marketing staff |
| [outreach_messages.md](outreach_messages.md) | LinkedIn and WhatsApp messages to book interviews |
| [bill_request.md](bill_request.md) | Asking for anonymised cooling bills, plus the exact fields to collect |
| [findings_template.md](findings_template.md) | Per-interview notes and the cross-interview synthesis. Copy it to `findings.md` and fill in the copy; the template stays blank |
| [interview_log.csv](interview_log.csv) | Tracker (participant codes only, never names) |

Anonymised bills go into [`data/real_bills/`](../../data/real_bills/README.md) using `template.csv`.

## Targets (3 weeks)

| Persona | Interviews | Why this many |
|---|---|---|
| Tenants (rented in Dubai within 2 years) | 8–10 | Main problem owner; patterns usually repeat after 6–8 |
| Brokers / leasing agents | 5 | The likely first paying channel (pilot) |
| Investors / landlords | 4 | Chiller-free pricing and net yield |
| Developers (product, design, sustainability, marketing) | 3 | Longer-term buyer; hardest to reach |
| **Anonymised bill sets** | 15+ units, 3+ months each, ideally including Jul/Aug | Needed for the real-world accuracy report |

Aim for a mix of cooling systems (district cooling, DEWA-billed split AC, chiller-free) and of facing directions. Ask every tenant whether their unit faces west. It's the cheapest test of our core claim.

## Rules for every interview

1. **Ask about past behaviour, not opinions about the future.** "Tell me about the last time you…" beats "Would you use…?" People are polite about ideas and accurate about their own history.
2. **Don't pitch until the last 5 minutes.** Discovery questions come first. The concept card comes last, so it can't colour the earlier answers.
3. **Get specifics.** Numbers, dates, which building type, which month the bill surprised them. "Expensive" means nothing until it's AED.
4. **Write quotes word for word,** or mark them as paraphrase. Never smooth a quote into what we hoped to hear.
5. **Consent first.** Say it's anonymous, ask before recording, and ask separately before collecting bill figures.
6. **No PII in this repo.** Use participant codes such as `T03` and `B02`. Keep contact details in your private notes, never in git.
7. **Never collect bill images,** names, unit numbers, account or premise numbers. Ask for the typed figures only (see `bill_request.md`).

## After each interview (10 minutes, same day)

1. Fill in one block of `findings.md` (your copy of `findings_template.md`).
2. Update `interview_log.csv`.
3. Score each hypothesis it touched: supports, contradicts or no signal.
4. If bills were shared, add rows to `data/real_bills/` and run `python tasks.py test`. The PII test must pass before you commit.

## When to stop and decide

After about 10 tenant and 5 broker interviews, review `hypotheses.md` against its thresholds. The decision rules there say whether to continue, narrow the scope, or pivot the segment.
