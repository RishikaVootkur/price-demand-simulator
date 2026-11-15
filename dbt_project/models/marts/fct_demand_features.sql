-- Model-ready features, one row per item, store, and day.
-- Sales-based features look back at least 7 days, so they are known one week before the day they describe.
-- Price features use today's price, because the retailer sets the price in advance.
with

enriched as (
    select * from {{ ref('int_sales_enriched') }}
),

windowed as (
    select
        *,
        sum(units_sold) over (
            partition by item_id, store_id order by day_number
            range between 7 preceding and 7 preceding
        ) as units_lag_7,
        sum(units_sold) over (
            partition by item_id, store_id order by day_number
            range between 28 preceding and 28 preceding
        ) as units_lag_28,
        avg(units_sold) over (
            partition by item_id, store_id order by day_number
            range between 13 preceding and 7 preceding
        ) as units_mean_7d_from_lag_7,
        avg(units_sold) over (
            partition by item_id, store_id order by day_number
            range between 34 preceding and 7 preceding
        ) as units_mean_28d_from_lag_7,
        avg(sell_price) over (
            partition by item_id, store_id order by day_number
            range between 28 preceding and 1 preceding
        ) as avg_price_prior_28d
    from enriched
)

select
    item_id,
    dept_id,
    category_id,
    store_id,
    state_id,
    day_number,
    calendar_date,
    units_sold,
    sell_price,
    avg_price_prior_28d,
    sell_price / avg_price_prior_28d - 1 as price_change_vs_prior_28d,
    cast(units_lag_7 as integer) as units_lag_7,
    cast(units_lag_28 as integer) as units_lag_28,
    units_mean_7d_from_lag_7,
    units_mean_28d_from_lag_7,
    day_of_week,
    month_number,
    calendar_year,
    event_name_1 is not null as is_event_day,
    coalesce('Sporting' in (event_type_1, event_type_2), false) as is_sporting_event,
    coalesce('Cultural' in (event_type_1, event_type_2), false) as is_cultural_event,
    coalesce('National' in (event_type_1, event_type_2), false) as is_national_event,
    coalesce('Religious' in (event_type_1, event_type_2), false) as is_religious_event,
    is_snap_day,
    temp_max_c,
    temp_min_c,
    precipitation_mm
from windowed
