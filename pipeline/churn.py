"""LightGBM churn (kayip musteri) modeli - notebooks/churn_clv.ipynb'deki
Adim 1-3 ve Adim 7'nin Airflow'un cagirabilecegi senkron hali.

Kapsamin disinda birakilanlar (bilerek): SHAP analizi ve CLV x churn risk
matrisi tek seferlik is yorumu/aciklanabilirlik calismalariydi, haftalik
otomatik calistirmanin parcasi degil - bu fonksiyon sadece modeli yeniden
egitip skorlari/tahminleri tazeler.

Sizinti (leakage) onleme: cutoff_date veri setinin SABIT bir tarihi degil,
`max(invoice_date) - 90 gun` olarak HER CALISTIRMADA yeniden hesaplanir -
boylece yeni islem verisi eklendiginde pipeline otomatik uyum saglar.
"""
import os

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split

from pipeline.db_utils import get_engine
from pipeline.mlflow_utils import promote_if_better

CHURN_MODEL_NAME = "customer-churn-lightgbm"
CHURN_WINDOW_DAYS = 90

FEATURE_QUERY = """
WITH bounds AS (
    SELECT (max(invoice_date)::date - INTERVAL '90 days')::date AS cutoff_date
    FROM transactions
),
pre_cutoff AS (
    SELECT t.*
    FROM transactions t, bounds b
    WHERE t.invoice_date::date <= b.cutoff_date
      AND t.quantity > 0 AND t.unit_price > 0
),
post_cutoff_activity AS (
    SELECT DISTINCT t.customer_id
    FROM transactions t, bounds b
    WHERE t.invoice_date::date > b.cutoff_date
      AND t.quantity > 0 AND t.unit_price > 0
)
SELECT
    p.customer_id,
    c.country,
    (b.cutoff_date - max(p.invoice_date)::date) AS recency,
    (b.cutoff_date - min(p.invoice_date)::date) AS tenure_days,
    count(DISTINCT p.invoice_id) AS frequency,
    sum(p.quantity * p.unit_price) AS monetary,
    sum(p.quantity * p.unit_price) / count(DISTINCT p.invoice_id) AS avg_order_value,
    count(DISTINCT p.stock_code) AS distinct_products,
    CASE WHEN pca.customer_id IS NULL THEN 1 ELSE 0 END AS churn
FROM pre_cutoff p
JOIN customers c ON c.customer_id = p.customer_id
CROSS JOIN bounds b
LEFT JOIN post_cutoff_activity pca ON pca.customer_id = p.customer_id
GROUP BY p.customer_id, c.country, b.cutoff_date, pca.customer_id
"""


def run_churn_training():
    engine = get_engine()
    df = pd.read_sql(FEATURE_QUERY, engine)
    df = df.set_index("customer_id")

    X = df.drop(columns=["churn"]).copy()
    X["country"] = X["country"].astype("category")
    y = df["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = lgb.LGBMClassifier(random_state=42, verbose=-1)
    model.fit(X_train, y_train, categorical_feature=["country"])

    test_proba = model.predict_proba(X_test)[:, 1]
    pr_auc = average_precision_score(y_test, test_proba)
    baseline_pr_auc = y_test.mean()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    mlflow.set_experiment("customer-churn-clv")
    client = MlflowClient()

    with mlflow.start_run(run_name="airflow_weekly_churn"):
        mlflow.log_param("churn_definition", f"{CHURN_WINDOW_DAYS} gun islem yok (cutoff sonrasi)")
        mlflow.log_param("n_features", X.shape[1])
        mlflow.log_metric("pr_auc", pr_auc)
        mlflow.log_metric("pr_auc_baseline", baseline_pr_auc)

        model_info = mlflow.lightgbm.log_model(model, name="model", registered_model_name=CHURN_MODEL_NAME)

    new_version = model_info.registered_model_version
    promoted = promote_if_better(client, CHURN_MODEL_NAME, new_version, "pr_auc", higher_is_better=True)

    churn_proba_all = pd.Series(model.predict_proba(X)[:, 1], index=X.index, name="churn_probability")
    out = churn_proba_all.reset_index()
    out.columns = ["customer_id", "churn_probability"]
    out["model_version"] = f"{CHURN_MODEL_NAME}:v{new_version}"
    out.to_sql("churn_predictions", engine, if_exists="append", index=False, method="multi", chunksize=1000)

    print(f"Churn: {len(out)} musteri icin tahmin yazildi, pr_auc={pr_auc:.4f}, promoted={promoted}")
    return {
        "version": new_version,
        "pr_auc": pr_auc,
        "pr_auc_baseline": baseline_pr_auc,
        "promoted": promoted,
        "customers_scored": len(out),
    }


if __name__ == "__main__":
    run_churn_training()
