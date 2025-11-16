CREATE TABLE IF NOT EXISTS dim_user (
    user_id        INT PRIMARY KEY,       -- from users.id
    email          VARCHAR(255) NOT NULL,
    username       VARCHAR(100) NOT NULL,
    first_name     VARCHAR(100),
    last_name      VARCHAR(100),
    phone          VARCHAR(50),

    city           VARCHAR(100),
    street         VARCHAR(100),
    street_number  INT,
    zipcode        VARCHAR(20),

    geo_lat        DECIMAL(10,6),
    geo_long       DECIMAL(10,6),

    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
