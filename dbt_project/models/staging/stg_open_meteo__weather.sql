-- One row per state and day. Units: degrees Celsius and millimetres.
select
    state_id,
    date as calendar_date,
    temperature_2m_max as temp_max_c,
    temperature_2m_min as temp_min_c,
    precipitation_sum as precipitation_mm
from {{ source('open_meteo', 'weather') }}
