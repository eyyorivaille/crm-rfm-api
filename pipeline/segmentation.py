"""K-Means musteri segmentasyonu - Mini Proje 2'deki final pipeline'in
(log1p + StandardScaler + K=5) Airflow tarafindan haftalik calistirilabilen hali.

NOT - Production'a OTOMATIK TERFI YOK: silhouette skoru kumeleme icin
yaniltici olabiliyor (bkz. notebooks/mlflow_utils.py'deki uyari - K=2 ve
bu projenin baseline'i, yuksek skorlu ama dengesiz/anlamsiz kumeler
uretmisti). Bu fonksiyon yeni versiyonu MLflow'a "Candidate" olarak
kaydeder; Production'a alinmasi icin kume buyukluklerine bakan bir
insanin MLflow UI'dan elle onay vermesi gerekir.
"""
import os

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from pipeline.db_utils import get_engine

MODEL_NAME = "rfm-customer-segments"
FINAL_K = 5

RFM_QUERY = """
    SELECT DISTINCT ON (customer_id) customer_id, recency, frequency, monetary
    FROM segments
    ORDER BY customer_id, calculated_at DESC
"""


def run_segmentation():
    engine = get_engine()
    with engine.connect() as conn:
        rfm = pd.read_sql(RFM_QUERY, conn).set_index("customer_id")

    pipeline = Pipeline([
        ("log_transform", ColumnTransformer(
            [("log", FunctionTransformer(np.log1p), ["frequency", "monetary"])],
            remainder="passthrough",
        )),
        ("scaler", StandardScaler()),
        ("kmeans", KMeans(n_clusters=FINAL_K, random_state=42, n_init=10)),
    ])
    pipeline.fit(rfm)
    labels = pipeline.predict(rfm)

    transformed = pipeline.named_steps["scaler"].transform(
        pipeline.named_steps["log_transform"].transform(rfm)
    )
    silhouette = silhouette_score(transformed, labels)
    cluster_sizes = sorted(pd.Series(labels).value_counts().tolist())

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    mlflow.set_experiment("rfm-kmeans-mini-proje-2")
    client = MlflowClient()

    with mlflow.start_run(run_name="airflow_weekly_segmentation"):
        mlflow.log_param("k", FINAL_K)
        mlflow.log_param("preprocessing", "log1p(frequency,monetary) + StandardScaler")
        mlflow.log_param("cluster_sizes", str(cluster_sizes))
        mlflow.log_metric("silhouette", silhouette)
        mlflow.log_metric("inertia", pipeline.named_steps["kmeans"].inertia_)

        model_info = mlflow.sklearn.log_model(pipeline, name="model", registered_model_name=MODEL_NAME)

    new_version = model_info.registered_model_version
    client.set_model_version_tag(MODEL_NAME, new_version, "stage", "Candidate")

    print(
        f"{MODEL_NAME} v{new_version} kaydedildi (Candidate) - "
        f"silhouette={silhouette:.4f}, kume buyuklukleri={cluster_sizes}"
    )
    print("Production'a terfi icin MLflow UI'dan elle onay gerekiyor.")

    return {"version": new_version, "silhouette": silhouette, "cluster_sizes": cluster_sizes}


if __name__ == "__main__":
    run_segmentation()
