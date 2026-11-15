-- Recompute units_lag_7 with a plain self-join and return any row where it disagrees.
-- Limited to one store to keep the test fast.
with features as (
    select item_id, store_id, day_number, units_sold, units_lag_7
    from {{ ref('fct_demand_features') }}
    where store_id = 'CA_1'
)

select
    today.item_id,
    today.day_number,
    today.units_lag_7,
    week_ago.units_sold as expected_units_lag_7
from features as today
left join features as week_ago
    on
        today.item_id = week_ago.item_id
        and today.store_id = week_ago.store_id
        and today.day_number - 7 = week_ago.day_number
where today.units_lag_7 is distinct from week_ago.units_sold
