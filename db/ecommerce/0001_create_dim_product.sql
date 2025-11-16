CREATE TABLE IF NOT EXISTS dim_product (
    product_id     INT PRIMARY KEY,       -- from products.id
    title          VARCHAR(255) NOT NULL,
    category       VARCHAR(100) NOT NULL,
    price          DECIMAL(10,2) NOT NULL,
    description    TEXT,
    image_url      VARCHAR(512),
    rating_rate    DECIMAL(3,1),
    rating_count   INT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
