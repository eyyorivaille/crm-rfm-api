-- RFM (Recency, Frequency, Monetary) skorlarini hesaplar ve segments tablosuna yazar.
-- Iade (quantity < 0) ve anormal (unit_price <= 0) satirlar haric tutulur.

WITH base AS (
    SELECT * FROM transactions WHERE quantity > 0 AND unit_price > 0
),
ref AS (
    SELECT max(invoice_date)::date AS ref_date FROM base
),
rfm_raw AS (
    SELECT
        b.customer_id,
        (ref.ref_date - max(b.invoice_date)::date) AS recency,
        count(DISTINCT b.invoice_id) AS frequency,
        sum(b.quantity * b.unit_price) AS monetary
    FROM base b, ref
    GROUP BY b.customer_id, ref.ref_date
),
scored AS (
    SELECT
        customer_id, recency, frequency, monetary,
        NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
    FROM rfm_raw
)
INSERT INTO segments (customer_id, recency, frequency, monetary, rfm_score, segment_label)
SELECT
    customer_id, recency, frequency, monetary,
    (r_score::text || f_score::text || m_score::text) AS rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champion'
        WHEN r_score >= 4 AND f_score = 1 THEN 'New Customer'
        WHEN r_score >= 3 AND f_score >= 4 THEN 'Loyal Customer'
        WHEN r_score >= 4 AND f_score <= 3 THEN 'Potential Loyalist'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating'
        ELSE 'Need Attention'
    END AS segment_label
FROM scored
RETURNING calculated_at;
