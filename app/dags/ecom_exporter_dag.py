from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Path assumptions inside the Airflow container:
# - GitSync clones the whole repo under /opt/airflow/dags/repo
# - dbt project lives under /opt/airflow/dags/repo/dbt
REPO_ROOT = "/opt/airflow/dags/repo"
DBT_PROJECT_DIR = os.path.join(REPO_ROOT, "dbt")

# Import your exporter
# (app/dags is on the Python path, so 'utils' is resolvable)
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
    dag_id="ecom_exporter_dag",
    description="Export e-commerce data and run dbt models",
    default_args=default_args,
    start_date=datetime(2025, 11, 1),
    schedule="0 5 * * *",     # daily at 05:00 UTC
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
            "cd {{ params.dbt_dir }} && "
            "DBT_PROFILES_DIR={{ params.dbt_dir }} "
            "dbt run --project-dir {{ params.dbt_dir }} "
            "--profiles-dir {{ params.dbt_dir }}"
        ),
        params={"dbt_dir": DBT_PROJECT_DIR},
    )

    # dbt test
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd {{ params.dbt_dir }} && "
            "DBT_PROFILES_DIR={{ params.dbt_dir }} "
            "dbt test --project-dir {{ params.dbt_dir }} "
            "--profiles-dir {{ params.dbt_dir }}"
        ),
        params={"dbt_dir": DBT_PROJECT_DIR},
    )

    export_task >> dbt_run >> dbt_test
