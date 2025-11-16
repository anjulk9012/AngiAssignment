with src as (
    select
        cast(json_extract(json_data, '$.id') as int)                         as user_id,
        json_unquote(json_extract(json_data, '$.email'))                    as email,
        json_unquote(json_extract(json_data, '$.username'))                 as username,
        json_unquote(json_extract(json_data, '$.name.firstname'))           as first_name,
        json_unquote(json_extract(json_data, '$.name.lastname'))            as last_name,
        json_unquote(json_extract(json_data, '$.address.city'))             as city,
        json_unquote(json_extract(json_data, '$.address.street'))           as street,
        json_unquote(json_extract(json_data, '$.address.number'))           as street_number,
        json_unquote(json_extract(json_data, '$.address.zipcode'))          as zipcode,
        cast(json_extract(json_data, '$.address.geolocation.lat') as decimal(10,6))  as latitude,
        cast(json_extract(json_data, '$.address.geolocation.long') as decimal(10,6)) as longitude
    from {{ source('ecommerce_raw', 'raw_users') }}
)

select * from src;
