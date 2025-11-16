CREATE TABLE IF NOT EXISTS fact_order_line (
    order_line_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id       INT NOT NULL,
    order_ts       DATETIME NOT NULL,
    user_id        INT NOT NULL,
    product_id     INT NOT NULL,
    quantity       INT NOT NULL,

    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_fact_user
        FOREIGN KEY (user_id) REFERENCES dim_user(user_id),
    CONSTRAINT fk_fact_product
        FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);
