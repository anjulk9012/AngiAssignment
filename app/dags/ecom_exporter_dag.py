from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Import your exporter script as a module
# Make sure utils/ecom_app.py is in the same repo (GitSync) as this DAG
import utils.ecom_app as ecom_app


def run_ecom_exporter(**kwargs):
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

# Path to dbt project inside the Airflow worker container
DBT_DIR = "/opt/airflow/dags/repo/dbt"

with DAG(
    dag_id="ecom_exporter_dbt_pipeline",
    description="Export ecommerce data and run dbt pipeline on MySQL",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",  # 05:00 UTC daily
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "dbt"],
) as dag:

    export_task = PythonOperator(
        task_id="run_ecom_exporter",
        python_callable=run_ecom_exporter,
    )

    dbt_debug = BashOperator(
        task_id="dbt_debug",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} dbt debug"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} dbt run"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} dbt test"
        ),
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} dbt docs generate"
        ),
    )

    # Order: export -> dbt_debug -> dbt_run -> dbt_test -> dbt_docs
    export_task >> dbt_debug >> dbt_run >> dbt_test >> dbt_docs
