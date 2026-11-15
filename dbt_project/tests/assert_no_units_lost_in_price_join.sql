-- int_sales_enriched drops days with no price (before the item was on sale).
-- That is only safe if those days sold nothing, so total units must match staging.
with

staged as (
    select sum(units_sold) as total_units from {{ ref('stg_m5__sales') }}
),

enriched as (
    select sum(units_sold) as total_units from {{ ref('int_sales_enriched') }}
)

select
    staged.total_units as staged_units,
    enriched.total_units as enriched_units
from staged
cross join enriched
where staged.total_units != enriched.total_units
