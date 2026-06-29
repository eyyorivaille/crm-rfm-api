"""BG/NBD + Gamma-Gamma (Lifetimes) ile 6 aylik CLV tahmini -
notebooks/churn_clv.ipynb'deki Adim 5 ve Adim 7'nin Airflow'un
cagirabilecegi senkron hali.

Kapsamin disinda birakilan (bilerek): CLV x churn risk matrisi ve uc-deger
(outlier) cap/filtreleme tek seferlik is yorumu calismasiydi - bu fonksiyon
ham predicted_clv_6m'i hesaplayip yazar, capping/segmentasyon bunu okuyan
analiz tarafinin isi (bkz. churn_clv.ipynb Adim 6).
"""
import os

import mlflow
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import calibration_and_holdout_data, summary_data_from_transaction_data
from mlflow.tracking import MlflowClient

from pipeline.db_utils import get_engine
from pipeline.mlflow_utils import promote_if_better

CLV_MODEL_NAME = "customer-clv-bgnbd-gammagamma"
PENALIZER_COEF = 0.001
TIME_HORIZON_MONTHS = 6
HOLDOUT_DAYS = 180

INVOICE_QUERY = """
    SELECT customer_id, invoice_id, min(invoice_date) AS invoice_date,
           sum(quantity * unit_price) AS invoice_value
    FROM transactions
    WHERE quantity > 0 AND unit_price > 0
    GROUP BY customer_id, invoice_id
"""


class CLVModel(mlflow.pyfunc.PythonModel):
    def __init__(self, bgf, ggf, time_months=TIME_HORIZON_MONTHS):
        self.bgf = bgf
        self.ggf = ggf
        self.time_months = time_months

    def predict(self, context, model_input):
        return self.ggf.customer_lifetime_value(
            self.bgf,
            model_input["frequency"],
            model_input["recency"],
            model_input["T"],
            model_input["monetary_value"],
            time=self.time_months,
            freq="D",
            discount_rate=0.01,
        )


def run_clv_training():
    engine = get_engine()
    invoices = pd.read_sql(INVOICE_QUERY, engine)
    max_date = invoices["invoice_date"].max()

    calibration_end = max_date - pd.Timedelta(days=HOLDOUT_DAYS)
    cal_holdout = calibration_and_holdout_data(
        invoices, customer_id_col="customer_id", datetime_col="invoice_date",
        calibration_period_end=calibration_end, observation_period_end=max_date,
        freq="D", monetary_value_col="invoice_value",
    )

    bgf_cal = BetaGeoFitter(penalizer_coef=PENALIZER_COEF)
    bgf_cal.fit(cal_holdout["frequency_cal"], cal_holdout["recency_cal"], cal_holdout["T_cal"])
    predicted_holdout = bgf_cal.predict(
        HOLDOUT_DAYS, cal_holdout["frequency_cal"], cal_holdout["recency_cal"], cal_holdout["T_cal"]
    )
    actual_holdout = cal_holdout["frequency_holdout"]
    mae = (predicted_holdout - actual_holdout).abs().mean()
    corr = predicted_holdout.corr(actual_holdout)

    summary_full = summary_data_from_transaction_data(
        invoices, "customer_id", "invoice_date",
        monetary_value_col="invoice_value", observation_period_end=max_date, freq="D",
    )
    bgf = BetaGeoFitter(penalizer_coef=PENALIZER_COEF)
    bgf.fit(summary_full["frequency"], summary_full["recency"], summary_full["T"])

    repeat_customers = summary_full[summary_full["frequency"] > 0]
    ggf = GammaGammaFitter(penalizer_coef=PENALIZER_COEF)
    ggf.fit(repeat_customers["frequency"], repeat_customers["monetary_value"])

    clv_repeat = ggf.customer_lifetime_value(
        bgf, repeat_customers["frequency"], repeat_customers["recency"],
        repeat_customers["T"], repeat_customers["monetary_value"],
        time=TIME_HORIZON_MONTHS, freq="D", discount_rate=0.01,
    )
    clv_result = summary_full.copy()
    clv_result["predicted_clv_6m"] = clv_repeat.reindex(clv_result.index)
    clv_result["has_repeat_history"] = clv_result["frequency"] > 0

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    mlflow.set_experiment("customer-churn-clv")
    client = MlflowClient()

    with mlflow.start_run(run_name="airflow_weekly_clv"):
        mlflow.log_param("penalizer_coef", PENALIZER_COEF)
        mlflow.log_param("time_horizon_months", TIME_HORIZON_MONTHS)
        mlflow.log_param("n_repeat_customers", len(repeat_customers))
        mlflow.log_metric("calibration_mae", mae)
        mlflow.log_metric("calibration_correlation", corr)

        model_info = mlflow.pyfunc.log_model(
            name="model", python_model=CLVModel(bgf, ggf), registered_model_name=CLV_MODEL_NAME,
        )

    new_version = model_info.registered_model_version
    promoted = promote_if_better(client, CLV_MODEL_NAME, new_version, "calibration_correlation", higher_is_better=True)

    clv_out = clv_result[["predicted_clv_6m", "has_repeat_history"]].reset_index()
    clv_out.columns = ["customer_id", "predicted_clv_6m", "has_repeat_history"]
    clv_out["model_version"] = f"{CLV_MODEL_NAME}:v{new_version}"
    clv_out.to_sql("clv_predictions", engine, if_exists="append", index=False, method="multi", chunksize=1000)

    print(f"CLV: {len(clv_out)} musteri icin tahmin yazildi, calibration_corr={corr:.4f}, promoted={promoted}")
    return {
        "version": new_version,
        "calibration_mae": mae,
        "calibration_correlation": corr,
        "promoted": promoted,
        "customers_scored": len(clv_out),
    }


if __name__ == "__main__":
    run_clv_training()
