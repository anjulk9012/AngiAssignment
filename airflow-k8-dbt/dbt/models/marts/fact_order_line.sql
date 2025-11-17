with src as (
    select
        order_id,
        order_ts,
        user_id,
        product_id,
        quantity
    from {{ ref('stg_order_lines') }}
)

select
    order_id,
    order_ts,
    user_id,
    product_id,
    quantity
from src;
