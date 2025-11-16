select
    user_id,
    email,
    username,
    first_name,
    last_name,
    city,
    street,
    street_number,
    zipcode,
    latitude,
    longitude
from {{ ref('stg_users') }};
