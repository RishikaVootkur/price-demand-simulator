-- One row per day. Bridges sales (day_number) to dates and to prices (week_id).
select
    cast(replace(d, 'd_', '') as integer) as day_number,
    date as calendar_date,
    wm_yr_wk as week_id,
    -- week_id jumps at year ends (11152 -> 11201); week_number counts 1, 2, 3, ... with no jumps
    dense_rank() over (order by wm_yr_wk) as week_number,
    weekday as weekday_name,
    month as month_number,
    year as calendar_year,
    event_name_1,
    event_type_1,
    event_name_2,
    event_type_2,
    cast(snap_ca as boolean) as is_snap_ca,
    cast(snap_tx as boolean) as is_snap_tx,
    cast(snap_wi as boolean) as is_snap_wi
from {{ source('m5', 'calendar') }}
