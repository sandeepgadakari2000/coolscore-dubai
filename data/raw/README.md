# Raw data cache

Created by `python tasks.py data` (network, about 30 s). Everything else in CoolScore reads these files offline.

| Path | What | Committed |
|---|---|---|
| `weather/dubai_<site>_<year>.csv.gz` (+ `.meta.json`) | **Canonical weather**: ECMWF IFS 9 km hourly, temperature and dew point bias-corrected to airport observations, RH recomputed. Local Dubai time (UTC+4); radiation = preceding-hour mean | yes |
| `weather/openmeteo_ecmwf_ifs_<site>_<year>.csv.gz` | Raw model output as downloaded (provenance) | yes |
| `weather/validation/ecmwf_ifs_<station>.csv.gz` etc. | Raw model output at the airport coordinates, used to fit and test the correction | yes |
| `weather/bias_correction.csv` | Additive correction per station × month × hour (°C) | yes |
| `weather/phase1_summary.json` | Validation statistics feeding `docs/evidence/weather.md` | yes |
| `stations/isd_<station>_<year>.csv.gz` | NOAA ISD hourly temperature and dew point at Dubai International and Al Maktoum | yes |
| `facade/facade_<site>_<year>.csv.gz` | Beam and sky-diffuse sun on 8 vertical orientations (pvlib). Derived; rebuilt automatically on first use | no (gitignored) |

Columns: `temp_c`, `rh_pct`, `dewpoint_c`, `pressure_hpa`, `wind_ms` (10 m), `ghi_wm2`, `bhi_wm2` (beam horizontal),
`dhi_wm2` (diffuse horizontal), `dni_wm2`, `cloud_pct`.

## Attribution and licences

- **Weather data by [Open-Meteo.com](https://open-meteo.com/)**, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Modified: temperature and dew point bias-corrected, relative humidity recomputed. The free API tier is for non-commercial use only.
- **Observations**: NOAA National Centers for Environmental Information, Integrated Surface Database (global-hourly), US government open data.
