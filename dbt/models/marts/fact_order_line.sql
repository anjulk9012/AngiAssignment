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
    -- natural keys as FKs; surrogate key is auto in MySQL table
    order_id,
    order_ts,
    user_id,
    product_id,
    quantity
from src;
