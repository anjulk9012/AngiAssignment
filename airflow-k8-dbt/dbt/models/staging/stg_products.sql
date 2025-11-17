with src as (
    select
        cast(json_extract(json_data, '$.id') as int)          as product_id,
        json_unquote(json_extract(json_data, '$.title'))      as title,
        json_unquote(json_extract(json_data, '$.category'))   as category,
        cast(json_extract(json_data, '$.price') as decimal(10,2)) as price,
        cast(json_extract(json_data, '$.rating.rate') as decimal(3,2))  as rating_rate,
        cast(json_extract(json_data, '$.rating.count') as int) as rating_count
    from {{ source('ecommerce_raw', 'raw_products') }}
)

select * from src;
