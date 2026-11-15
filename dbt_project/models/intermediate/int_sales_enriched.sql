-- One row per item, store, and day the item was on sale, with its price, calendar, and weather.
with

sales as (
    select * from {{ ref('stg_m5__sales') }}
),

calendar as (
    select * from {{ ref('stg_m5__calendar') }}
),

prices as (
    select * from {{ ref('stg_m5__prices') }}
),

weather as (
    select * from {{ ref('stg_open_meteo__weather') }}
)

select
    sales.item_id,
    sales.dept_id,
    sales.category_id,
    sales.store_id,
    sales.state_id,
    sales.day_number,
    calendar.calendar_date,
    calendar.week_id,
    sales.units_sold,
    prices.sell_price,
    isodow(calendar.calendar_date) as day_of_week,  -- 1 = Monday ... 7 = Sunday
    calendar.month_number,
    calendar.calendar_year,
    calendar.event_name_1,
    calendar.event_type_1,
    calendar.event_name_2,
    calendar.event_type_2,
    case sales.state_id
        when 'CA' then calendar.is_snap_ca
        when 'TX' then calendar.is_snap_tx
        when 'WI' then calendar.is_snap_wi
    end as is_snap_day,
    weather.temp_max_c,
    weather.temp_min_c,
    weather.precipitation_mm

from sales
inner join calendar
    on sales.day_number = calendar.day_number
-- Inner join drops days before the item was on sale. Those days all have 0 units, so no sales are lost.
inner join prices
    on
        sales.item_id = prices.item_id
        and sales.store_id = prices.store_id
        and calendar.week_id = prices.week_id
left join weather
    on
        sales.state_id = weather.state_id
        and calendar.calendar_date = weather.calendar_date
