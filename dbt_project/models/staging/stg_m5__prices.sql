-- One row per item, store, and Walmart week. Items have no row in weeks they were not on sale.
select
    item_id,
    store_id,
    wm_yr_wk as week_id,
    cast(sell_price as decimal(10, 2)) as sell_price
from {{ source('m5', 'prices') }}
