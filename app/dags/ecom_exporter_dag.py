from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator

# Import your exporter script
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
        "ecom_exporter.py",
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

# Path to dbt project inside the Airflow container
DBT_DIR = "/opt/airflow/dags/repo/airflow-k8-dbt/dbt"
DBT_ENV = {
    "DBT_PROFILES_DIR": DBT_DIR,     # use profiles.yml from the project dir
}

with DAG(
    dag_id="ecom_exporter_dbt_pipeline",
    description="Export ecommerce data then run dbt pipeline on MySQL",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "dbt", "mysql"],
) as dag:

    export_task = PythonOperator(
        task_id="run_ecom_exporter",
        python_callable=run_ecom_exporter,
    )

    dbt_debug = BashOperator(
        task_id="dbt_debug",
        bash_command=f"cd {DBT_DIR} && dbt debug",
        env=DBT_ENV,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run",
        env=DBT_ENV,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
        env=DBT_ENV,
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_DIR} && dbt docs generate",
        env=DBT_ENV,
    )

    # Simple linear pipeline:
    # 1) export raw JSONL
    # 2) validate dbt project
    # 3) run models
    # 4) run tests
    # 5) build docs
    export_task >> dbt_debug >> dbt_run >> dbt_test >> dbt_docs_generate
