"""Bu modulun gercek implementasyonu pipeline/mlflow_utils.py'e tasindi
(Gun 17-18'de Airflow task'larinin da kullanabilmesi icin tek kaynak
haline getirildi). Bu dosya, mevcut notebook hücrelerindeki
`from mlflow_utils import promote_if_better` import'unu bozmamak icin
geriye-uyumlu bir yonlendirme (re-export) olarak birakildi.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.mlflow_utils import promote_if_better  # noqa: E402, F401
