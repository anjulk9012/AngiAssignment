# Start from official Airflow image
FROM apache/airflow:3.0.2

# ---- OS deps (optional, but mysql client can be useful) ----
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# ---- Python deps: install as airflow user (required by this image) ----
USER airflow

RUN pip install --no-cache-dir \
      requests \
      dbt-core \
      dbt-mysql

# ---- Copy dbt project into image ----
# Your repo structure has "dbt" at the root:
#   dbt/
#     dbt_project.yml
#     profiles.yml
#     models/
COPY dbt /opt/airflow/dbt

# Tell dbt where profiles.yml lives
ENV DBT_PROFILES_DIR=/opt/airflow/dbt

# ---- Optional: copy SQL migrations (if you want to use them elsewhere) ----
COPY db/ecommerce /opt/airflow/db/ecommerce

# We do NOT override CMD/ENTRYPOINT: Airflow's own entrypoint will still run
# webserver, scheduler, workers, etc. as configured by the Helm chart.
