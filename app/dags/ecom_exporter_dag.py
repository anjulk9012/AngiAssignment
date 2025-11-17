from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Import your exporter script as a module
# Repo layout: app/dags/utils/ecom_app.py
import utils.ecom_app as ecom_app


# ----- CONFIG: DBT PATHS -----
# GitSync clones repo to /opt/airflow/dags/repo by default
DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR", "/opt/airflow/dags/repo/dbt")
DBT_PROFILES_DIR = os.getenv("DBT_PROFILES_DIR", DBT_PROJECT_DIR)

# Environment passed to all dbt commands
DBT_ENV = {
    "DBT_PROFILES_DIR": DBT_PROFILES_DIR,
    # add DB credentials here if you prefer env-vars style, e.g.:
    # "DBT_MYSQL_USER": os.getenv("DBT_MYSQL_USER", "airflow"),
    # "DBT_MYSQL_PASSWORD": os.getenv("DBT_MYSQL_PASSWORD", "airflow_pass"),
}


def run_ecom_exporter(**_kwargs):
    """
    Wraps ecom_app.main() so we can call it from Airflow.
    We pass arguments via sys.argv because ecom_app.main()
    uses argparse to parse CLI arguments.
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

with DAG(
    dag_id="ecom_exporter_dbt_dag",
    description="Export e-commerce data from Fake Store API and run dbt pipeline",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",   # every day at 05:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "dbt", "jsonl"],
) as dag:

    # 1) Export raw data to JSONL
    export_task = PythonOperator(
        task_id="run_ecom_exporter",
        python_callable=run_ecom_exporter,
    )

    # 2) dbt test  (optional but nice to keep first)
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test",
        env=DBT_ENV,
    )

    # 3) dbt run  (build models)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run",
        env=DBT_ENV,
    )

    # 4) dbt docs generate  (build documentation)
    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt docs generate",
        env=DBT_ENV,
    )

    # Define task order: export -> dbt test -> dbt run -> dbt docs
    export_task >> dbt_test >> dbt_run >> dbt_docs
