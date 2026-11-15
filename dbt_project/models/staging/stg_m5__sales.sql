-- One row per item, store, and day. Raw sales are wide (one column per day), so unpivot them.

{#- Build the list of day columns (d_1 ... d_1941) from the raw table instead of typing them out. -#}
{%- set day_columns = [] -%}
{%- if execute -%}
    {%- for column in adapter.get_columns_in_relation(source('m5', 'sales')) -%}
        {%- if modules.re.match('^d_[0-9]+$', column.name) -%}
            {%- do day_columns.append(column.name) -%}
        {%- endif -%}
    {%- endfor -%}
    {%- if day_columns | length == 0 -%}
        {{ exceptions.raise_compiler_error("raw sales has no d_<n> day columns") }}
    {%- endif -%}
{%- endif %}

with

unpivoted as (
    -- include nulls: an empty raw cell becomes a NULL row (caught by not_null) instead of vanishing
    select *
    from {{ source('m5', 'sales') }}
    unpivot include nulls (units_sold for day_code in ({{ day_columns | join(', ') }}))
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
