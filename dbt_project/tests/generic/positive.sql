{#- Fails if any value is negative, or zero unless allow_zero is true. NULLs are left to not_null. -#}
{% test positive(model, column_name, allow_zero=false) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} {{ '<' if allow_zero else '<=' }} 0

{% endtest %}
