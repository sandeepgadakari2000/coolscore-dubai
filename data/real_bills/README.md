# Real cooling bills (anonymised)

This folder holds **real, anonymised** cooling-bill figures used to check the model against reality.
It starts empty except for `template.csv`. Nothing in here is simulated, and nothing may be invented.

## How to add bills

1. Copy `template.csv` to `bills.csv`, or append to it if it already exists. Use **one row per unit per bill month**.
2. Give each unit a code (`U001`, `U002`…) in `unit_ref` and each row a code (`R0001`…) in `record_id`. Never derive a code from a unit number.
3. Run `python tasks.py test`. The PII test fails if a forbidden column or a phone number, email or account-number-like value appears.
4. From Phase 8 onwards, `python tasks.py validate` (also run by the app) rebuilds the validation report automatically.

## Never store

Names, phone numbers, emails, unit or flat numbers, building or tower names, DEWA account or premise numbers, cooling account or contract numbers, Makani numbers, addresses, or any bill image or photo.
If someone sends a photo anyway: copy only the allowed fields below, then delete the photo from your phone and the chat.

## Fields

| Column | Format / allowed values | Notes |
|---|---|---|
| `record_id` | `R0001` | One per row |
| `unit_ref` | `U001` | Same code for all months of the same unit |
| `submitted_date` | `YYYY-MM-DD` | When you received the figures |
| `consent` | `yes` | Participant agreed to anonymised use, including publication in this repo. Never add rows without consent |
| `data_source` | `typed_by_participant` / `read_out_by_participant` | We never hold the bill itself |
| `community` | e.g. `Dubai Marina` | Community level only, never the building |
| `building_completion_year` | e.g. `2009`, or blank | Approximate is fine |
| `building_era_band` | `before_2005` / `2005_2014` / `2015_2021` / `2022_plus` / `unknown` | Bands match `config/archetypes.yaml` |
| `total_floors_band` | `low_rise_le10` / `mid_rise_11_25` / `high_rise_26_50` / `super_tall_51_plus` / `unknown` | |
| `floor_band` | `low_1_5` / `mid` / `high` / `top` / `unknown` | `top` = roof directly above the unit |
| `facing` | `N` `NE` `E` `SE` `S` `SW` `W` `NW`, corners as `W+N`, or `unknown` | The main living-room windows |
| `size_sqft` | integer, **rounded to the nearest 50** | Rounding lowers re-identification risk |
| `bedrooms` | `0` (studio) to `5` | |
| `glass_amount` | `low` / `medium` / `high` / `floor_to_ceiling` / `unknown` | |
| `balcony` | `none` / `small` / `deep` / `unknown` | `deep` ≈ 2 m or more |
| `view_obstruction` | `open` / `partial` / `heavy` / `unknown` | Neighbouring towers blocking the facade |
| `cooling_system` | `district_cooling` / `dewa_split_ac` / `dewa_central_ac` / `building_central_plant` / `unknown` | |
| `cooling_payer` | `tenant` / `landlord_chiller_free` / `service_charge` / `unknown` | |
| `cooling_provider` | free text or blank | Provider type or company (data only, never shown in the UI) |
| `contracted_capacity_rt` | number or blank | Often printed on district-cooling bills. Very valuable |
| `household_size` | integer | |
| `home_daytime` | `yes` / `no` / `partly` | |
| `typical_setpoint_c` | number or blank | |
| `bill_month` | `YYYY-MM` | The month the consumption happened |
| `dc_consumption_rth` | number | District cooling consumption, ton-hours |
| `dc_consumption_aed` | AED | Consumption charge |
| `dc_capacity_aed` | AED | Capacity / demand charge |
| `dc_fuel_surcharge_aed` | AED | If shown |
| `dc_meter_admin_aed` | AED | Meter, admin, billing fees |
| `dc_vat_aed` | AED | |
| `dc_total_aed` | AED | Bill total for the month |
| `dewa_electricity_kwh` | kWh | Unit's DEWA electricity for the month |
| `dewa_electricity_aed` | AED | Electricity charge only (not water, sewerage or housing fee) |
| `dewa_fuel_surcharge_aed` | AED | If shown |

Leave a cell blank if it's unknown. Don't guess.
