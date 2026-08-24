# Karnataka Socio-Economic Indicator Dataset (versioned)

**DEMO DATA.** This dataset exists so the Sociological Intelligence module can
compute correlations against plausible reference values during demos and
evaluation runs. It is not an official statistical publication.

Versioned dataset backing the Sociological Intelligence module
(`backend/app/services/sociological_service.py`). Loaded at runtime — the
module no longer hardcodes indicator values in code.

For production deployments the same rows live in the Supabase table
`socioeconomic_indicators` (see `backend/scripts/socioeconomic_indicators.sql`);
the bundled CSV is only the offline fallback.

## File

`karnataka_socioeconomic_indicators.csv`

| Column | Meaning | Source |
|---|---|---|
| `district` | Karnataka district name (must match `locations.district`) | Saksha registry |
| `population_lakhs` | District population in lakhs | Census of India 2011, Primary Census Abstract |
| `area_sq_km` | District area in sq km | Census of India 2011 |
| `literacy_rate` | Effective literacy rate (%) | Census of India 2011 |
| `sex_ratio` | Females per 1000 males | Census of India 2011 |
| `avg_income_lakhs` | Approx. annual per-capita income (Rs lakh) | Karnataka Economic Survey district estimates (approximation) |
| `unemployment_rate` | Unemployment rate (%), persons aged 15+ | PLFS 2023-24 state-level rate distributed across districts (approximation) |
| `urbanization_type` | urban / semi_urban / rural classification | Derived from Census urban share |
| `urbanization_share_pct` | % of population living in statutory towns | Census of India 2011 |
| `data_year` | Primary source year | — |

## Honesty notes

- Census columns (`population_lakhs`, `area_sq_km`, `literacy_rate`, `sex_ratio`,
  `urbanization_share_pct`) are genuine Census 2011 figures.
- `avg_income_lakhs` and `unemployment_rate` are **approximations** derived from
  state-level Economic Survey / PLFS publications; district values are indicative,
  not official statistics. The API labels them accordingly via `data_year` and the
  `/sociological/dataset-info` endpoint.
- `Vijayanagara` was carved out of Ballari in 2020-21; its row carries Census-2011-era
  estimates so all 31 current districts can be represented. Treat it as indicative.

## Versioning

- `v1.0.0` (2026-08): initial release covering the 9 districts seeded in Saksha.
- `v2.0.0` (2026-08): expanded to all 30/31 Karnataka districts (incl. Vijayanagara);
  corrected Mysuru/Kalaburagi area values to Census 2011 figures. Bump the version and
  update rows when official indicators are wired in.
