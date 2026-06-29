"""Pipeline modulleri icin paylasilan, senkron veritabani baglantisi.

main.py/db.py'deki async engine'den bilerek ayri tutuluyor: Airflow
task'lari senkron Python callable'lar olarak calisir, FastAPI'nin event
loop'una bagli degildir.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


def get_logs_engine():
    """crm_db'den ayri - sadece pipeline_runs (Airflow orkestrasyon gecmisi) icin."""
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('LOGS_DB_NAME')}"
    )
