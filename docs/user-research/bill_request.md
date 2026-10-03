# Asking for anonymised cooling bills

Send this only to people who have already agreed in an interview, or who replied positively to outreach.
We collect **typed figures only**. No photos, no names, no unit numbers, no account numbers.

---

## Message (WhatsApp or email)

> Hi [Name], thanks again for the chat! As mentioned, real bill figures are the only way to check whether my cooling-cost estimates are right.
>
> If you're comfortable, could you **type out** these figures for 3 or more recent months (ideally including July/August)? Please **don't send a photo** of the bill. Just the numbers below, and skip anything you don't know:
>
> **About the flat** (no building name or unit number please)
> • Community (e.g., JLT, Business Bay)
> • Roughly when the building was finished
> • Floor: low (1–5), mid, high, or top floor
> • Which way the main windows face (N/E/S/W…)
> • Size (sq ft, roughly) and number of bedrooms
> • Glass: a little / a lot / floor-to-ceiling. Balcony: none / small / deep
> • Cooling: district cooling, DEWA-billed AC, or chiller-free?
> • If it's on the bill: contracted capacity in RT
> • How many people live there, is anyone home during the day, and your usual AC temperature
>
> **For each month**
> • Month and year
> • Cooling bill: consumption (RTh), consumption charge, capacity/demand charge, fuel surcharge, fees, VAT, total (AED)
> • DEWA electricity: kWh and electricity charge (AED), if you have them
>
> The figures will be stored anonymously (a code, not your name) and may be published in anonymised form as part of the project's accuracy report. Is that OK with you?
>
> Thank you, this genuinely helps!

## If you prefer a form

Create a short online form whose fields match the field list in [`data/real_bills/README.md`](../../data/real_bills/README.md).
Settings: don't collect email addresses, no file-upload question, and repeat the month section 3–12 times.
Put the consent sentence above as a required yes/no question at the top.

## After receiving figures

1. Transcribe into `data/real_bills/bills.csv` (one row per unit-month), using the participant's unit code (`U0xx`).
2. Delete the chat messages, or any photo that was sent despite the request.
3. Run `python tasks.py test` before committing. The PII test must pass.
4. Log it in `interview_log.csv` (`bills_shared = yes`, number of months).
