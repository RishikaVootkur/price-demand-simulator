-- Recompute lag and rolling-mean features with plain joins and return any row that disagrees.
-- Limited to one store to keep the test fast.
with

features as (
    select * from {{ ref('fct_demand_features') }}
    where store_id = 'CA_1'
),

expected as (
    select
        today.item_id,
        today.day_number,
        any_value(lag_7.units_sold) as expected_lag_7,
        any_value(lag_28.units_sold) as expected_lag_28,
        case when count(prior_week.units_sold) = 7 then avg(prior_week.units_sold) end as expected_mean_7d
    from features as today
    left join features as lag_7
        on today.item_id = lag_7.item_id and lag_7.day_number = today.day_number - 7
    left join features as lag_28
        on today.item_id = lag_28.item_id and lag_28.day_number = today.day_number - 28
    left join features as prior_week
        on
            today.item_id = prior_week.item_id
            and prior_week.day_number between today.day_number - 13 and today.day_number - 7
    group by today.item_id, today.day_number
)

select
    features.item_id,
    features.day_number,
    features.units_lag_7,
    expected.expected_lag_7,
    features.units_lag_28,
    expected.expected_lag_28,
    features.units_mean_7d_from_lag_7,
    expected.expected_mean_7d
from features
inner join expected
    on features.item_id = expected.item_id and features.day_number = expected.day_number
where
    features.units_lag_7 is distinct from expected.expected_lag_7
    or features.units_lag_28 is distinct from expected.expected_lag_28
    or abs(coalesce(features.units_mean_7d_from_lag_7, -1) - coalesce(expected.expected_mean_7d, -1)) > 1e-9
