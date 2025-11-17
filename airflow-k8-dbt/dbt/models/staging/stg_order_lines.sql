with src as (
    select
        cast(json_extract(json_data, '$.order_id') as int)                          as order_id,
        cast(json_unquote(json_extract(json_data, '$.order_ts')) as datetime)       as order_ts,
        cast(json_extract(json_data, '$.user_id') as int)                           as user_id,
        cast(json_extract(json_data, '$.product_id') as int)                        as product_id,
        cast(json_extract(json_data, '$.quantity') as int)                          as quantity
    from {{ source('ecommerce_raw', 'raw_order_lines') }}
)

select * from src;
