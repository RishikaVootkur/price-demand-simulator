-- One row per item, store, and day. Raw sales are wide (one column per day), so unpivot them.
with

source as (
    select * from {{ source('m5', 'sales') }}
),

unpivoted as (
    unpivot source
    on columns('^d_[0-9]+$')
    into name day_code value units_sold
)

select
    item_id,
    dept_id,
    cat_id as category_id,
    store_id,
    state_id,
    cast(replace(day_code, 'd_', '') as integer) as day_number,
    cast(units_sold as integer) as units_sold
from unpivoted
