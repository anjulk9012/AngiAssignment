from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# so "utils.ecom_app" can be imported when dag is under app/dags/
CURRENT_DIR = os.path.dirname(__file__)
sys.path.append(CURRENT_DIR)

import utils.ecom_app as ecom_app


def run_ecom_exporter(**kwargs):
    """
    Wraps ecom_app.main() so we can call it from Airflow.
    """
    base_url = os.getenv("ECOM_BASE_URL", "https://fakestoreapi.com")
    dataset = os.getenv("ECOM_DATASET", "ecommerce")
    outdir = os.getenv("ECOM_OUTDIR", "/opt/airflow/data")
    timeout = os.getenv("HTTP_TIMEOUT", "30")
    sleep = os.getenv("HTTP_SLEEP", "0.25")

    argv = [
        "ecom_app.py",
        "--base-url", base_url,
        "--dataset", dataset,
        "--outdir", outdir,
        "--timeout", timeout,
        "--sleep", sleep,
        "--with-derived",
    ]
    sys.argv = argv
    ecom_app.main()


default_args = {
    "owner": "data-eng",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

DBT_ROOT = "/opt/airflow/dags/repo/dbt"
DBT_ENV = f"cd {DBT_ROOT} && DBT_PROFILES_DIR={DBT_ROOT}"

with DAG(
    dag_id="ecom_exporter_dbt_pipeline",
    description="Export FakeStore data then run dbt models on MySQL",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",  # every day at 05:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "dbt"],
) as dag:

    export_raw = PythonOperator(
        task_id="export_raw_ecommerce",
        python_callable=run_ecom_exporter,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f'{DBT_ENV} dbt run',
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f'{DBT_ENV} dbt test',
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f'{DBT_ENV} dbt docs generate',
    )

    # pipeline: export → run → test → docs
    export_raw >> dbt_run >> dbt_test >> dbt_docs
