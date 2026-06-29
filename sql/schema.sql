CREATE TABLE customers (
    customer_id     VARCHAR(20) PRIMARY KEY,
    country         VARCHAR(50),
    first_seen      DATE,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE transactions (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(20) NOT NULL,
    customer_id     VARCHAR(20) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    stock_code      VARCHAR(20) NOT NULL,
    description     VARCHAR(255),
    quantity        INTEGER,
    invoice_date    TIMESTAMP,
    unit_price      NUMERIC(10,2)
);

CREATE TABLE segments (
    customer_id     VARCHAR(20) NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    recency         INTEGER,
    frequency       INTEGER,
    monetary        NUMERIC(12,2),
    rfm_score       VARCHAR(5),
    segment_label   VARCHAR(30),
    calculated_at   TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (customer_id, calculated_at)
);

CREATE TABLE model_logs (
    log_id          SERIAL PRIMARY KEY,
    model_name      VARCHAR(50),
    run_at          TIMESTAMP DEFAULT now(),
    parameters      JSONB,
    metrics         JSONB,
    notes           TEXT
);

CREATE INDEX idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX idx_transactions_invoice_date ON transactions(invoice_date);
CREATE INDEX idx_transactions_invoice_stock ON transactions(invoice_id, stock_code);

CREATE TABLE churn_predictions (
    customer_id        VARCHAR(20) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    churn_probability  NUMERIC(6,5),
    predicted_at       TIMESTAMP NOT NULL DEFAULT now(),
    model_version      VARCHAR(100),
    PRIMARY KEY (customer_id, predicted_at)
);

CREATE TABLE clv_predictions (
    customer_id         VARCHAR(20) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    predicted_clv_6m    NUMERIC(14,2),
    has_repeat_history  BOOLEAN,
    predicted_at        TIMESTAMP NOT NULL DEFAULT now(),
    model_version       VARCHAR(100),
    PRIMARY KEY (customer_id, predicted_at)
);
