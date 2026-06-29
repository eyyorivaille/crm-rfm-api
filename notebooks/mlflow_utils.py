"""Notebooklar arasinda paylasilan MLflow yardimcilari.

Sadece egitim/notebook tarafinda kullanilir - FastAPI uygulamasinin
runtime kodu (main.py) bu modulu import etmez.
"""


def promote_if_better(client, model_name, new_version, metric_key, higher_is_better=True):
    """Yeni versiyonu, mevcut 'production' alias'liyla karsilastirip sadece
    metrigi daha iyiyse Production yapar; degilse hicbir sey degistirmez.

    Bu fonksiyon, "metrigi her zaman dogru yorumlanabilen" modeller icin
    uygundur (orn. PR-AUC, calibration correlation - yuksek = acikca daha iyi).

    UYARI - K-Means/kumeleme modelleri icin KULLANMAYIN: silhouette skoru
    yaniltici olabilir (bkz. Gun 8-9 K=2 ve Mini Proje 2 baseline orneklari -
    yuksek skor, anlamsiz/dengesiz kumelerden gelebilir). Kumeleme modelinde
    "daha iyi" karari kume buyukluklerine bakan bir insan tarafindan verilmeli,
    bu yuzden o notebooklarda promosyon hala elle yapiliyor.
    """
    new_run = client.get_run(client.get_model_version(model_name, new_version).run_id)
    new_metric = new_run.data.metrics.get(metric_key)

    try:
        current_prod = client.get_model_version_by_alias(model_name, "production")
        current_run = client.get_run(current_prod.run_id)
        current_metric = current_run.data.metrics.get(metric_key)
    except Exception:
        current_prod = None
        current_metric = None

    is_better = (
        current_metric is None
        or (higher_is_better and new_metric > current_metric)
        or (not higher_is_better and new_metric < current_metric)
    )

    if is_better:
        client.set_registered_model_alias(model_name, "production", new_version)
        client.set_model_version_tag(model_name, new_version, "stage", "Production")
        if current_prod is not None:
            client.set_model_version_tag(model_name, current_prod.version, "stage", "Archived")
        print(
            f"{model_name} v{new_version} -> PRODUCTION "
            f"({metric_key}={new_metric:.4f} vs onceki={current_metric})"
        )
    else:
        client.set_model_version_tag(model_name, new_version, "stage", "Archived")
        print(
            f"{model_name} v{new_version} -> ARCHIVED, promote edilmedi "
            f"({metric_key}={new_metric:.4f} <= mevcut production={current_metric:.4f})"
        )

    return is_better
