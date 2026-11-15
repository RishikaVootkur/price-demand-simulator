-- Model-ready features, one row per item, store, and day.
-- Sales-based features look back at least 7 days, so they are known one week ahead.
-- Price features use the current week's price: the retailer plans its own prices in advance.
-- Calendar and weather describe the day itself; in production, weather would come from a forecast.
with

enriched as (
    select * from {{ ref('int_sales_enriched') }}
),

-- M5 has one price per item, store, and week, so compare prices week to week.
weekly_prices as (
    select
        item_id,
        store_id,
        week_number,
        any_value(sell_price) as sell_price
    from enriched
    group by item_id, store_id, week_number
),

weekly_price_history as (
    select
        item_id,
        store_id,
        week_number,
        avg(sell_price) over (
            partition by item_id, store_id order by week_number
            range between 4 preceding and 1 preceding
        ) as avg_price_prior_4wk
    from weekly_prices
),

windowed as (
    select
        enriched.*,
        weekly_price_history.avg_price_prior_4wk,
        max(enriched.units_sold) over (item_days range between 7 preceding and 7 preceding) as units_lag_7,
        max(enriched.units_sold) over (item_days range between 28 preceding and 28 preceding) as units_lag_28,
        -- Means are null unless every day in the window is present, so a short history never poses as a full one.
        case
            when count(enriched.units_sold) over (item_days range between 13 preceding and 7 preceding) = 7
                then avg(enriched.units_sold) over (item_days range between 13 preceding and 7 preceding)
        end as units_mean_7d_from_lag_7,
        case
            when count(enriched.units_sold) over (item_days range between 34 preceding and 7 preceding) = 28
                then avg(enriched.units_sold) over (item_days range between 34 preceding and 7 preceding)
        end as units_mean_28d_from_lag_7
    from enriched
    left join weekly_price_history
        on
            enriched.item_id = weekly_price_history.item_id
            and enriched.store_id = weekly_price_history.store_id
            and enriched.week_number = weekly_price_history.week_number
    window item_days as (partition by enriched.item_id, enriched.store_id order by enriched.day_number)
)

select
    item_id,
    dept_id,
    category_id,
    store_id,
    state_id,
    day_number,
    calendar_date,
    week_number,
    units_sold,
    sell_price,
    avg_price_prior_4wk,
    sell_price / avg_price_prior_4wk - 1 as price_change_vs_prior_4wk,
    units_lag_7,
    units_lag_28,
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
