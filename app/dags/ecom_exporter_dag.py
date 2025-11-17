from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Import your exporter script
# DAG file is at /opt/airflow/dags/repo/app/dags/ecom_exporter_dag.py
# utils module is at /opt/airflow/dags/repo/app/dags/utils/ecom_app.py
sys.path.append(os.path.dirname(__file__))  # ensure ./utils is on PYTHONPATH
import utils.ecom_app as ecom_app  # noqa: E402

# Paths for dbt inside the Airflow container (from GitSync)
DBT_PROJECT_DIR = "/opt/airflow/dags/repo/dbt"
DBT_PROFILES_DIR = DBT_PROJECT_DIR  # profiles.yml is in the same folder


def run_ecom_exporter(**kwargs):
    """
    Call ecom_app.main() with CLI-style args.
    """
    base_url = os.getenv("ECOM_BASE_URL", "https://fakestoreapi.com")
    dataset = os.getenv("ECOM_DATASET", "ecommerce")
    outdir = os.getenv("ECOM_OUTDIR", "/opt/airflow/data")
    timeout = os.getenv("HTTP_TIMEOUT", "30")
    sleep = os.getenv("HTTP_SLEEP", "0.25")

    argv = [
        "ecom_exporter.py",
        "--base-url",
        base_url,
        "--dataset",
        dataset,
        "--outdir",
        outdir,
        "--timeout",
        timeout,
        "--sleep",
        sleep,
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

with DAG(
    dag_id="ecom_exporter_dbt_pipeline",
    description="Export Fake Store data then run dbt models/tests/docs",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",  # daily at 05:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "dbt"],
) as dag:

    export_task = PythonOperator(
        task_id="run_ecom_exporter",
        python_callable=run_ecom_exporter,
    )

    # dbt run
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_PROFILES_DIR} dbt run"
        ),
    )

    # dbt test
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_PROFILES_DIR} dbt test"
        ),
    )

    # dbt docs generate
    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_PROFILES_DIR} dbt docs generate"
        ),
    )

    # Orchestration: export → dbt run → dbt test → dbt docs
    export_task >> dbt_run >> dbt_test >> dbt_docs
