from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import your exporter script as a module
# Make sure ecom_exporter.py is in the Python path used by Airflow workers
import utils.ecom_app as ecom_app


def run_ecom_exporter(**context):
    """
    Wraps ecom_exporter.main() so we can call it from Airflow.

    We pass arguments via sys.argv because ecom_exporter.main()
    uses argparse to parse CLI arguments.
    """
    # You can override these via env vars in your Airflow deployment if needed
    base_url = os.getenv("ECOM_BASE_URL", "https://fakestoreapi.com")
    dataset = os.getenv("ECOM_DATASET", "ecommerce")
    outdir = os.getenv("ECOM_OUTDIR", "/opt/airflow/data")
    timeout = os.getenv("HTTP_TIMEOUT", "30")
    sleep = os.getenv("HTTP_SLEEP", "0.25")

    # Build CLI-style arguments
    argv = [
        "ecom_exporter.py",
        "--base-url", base_url,
        "--dataset", dataset,
        "--outdir", outdir,
        "--timeout", timeout,
        "--sleep", sleep,
        "--with-derived",          # we always want derived order_lines
    ]

    # Set sys.argv so argparse inside main() sees our args
    sys.argv = argv

    # Call the script's main entrypoint
    ecom_app.main()


default_args = {
    "owner": "data-eng",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="ecom_exporter_dag",
    description="Export e-commerce data from Fake Store API to partitioned JSONL",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["ecommerce", "export", "jsonl"],
) as dag:

    export_task = PythonOperator(
        task_id="run_ecom_exporter",
        python_callable=run_ecom_exporter,
        provide_context=True,
    )

    export_task
