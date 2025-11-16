FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests

# Copy your exporter script (adjust path if needed)
# If ecom_app.py is your exporter, keep the name consistent
COPY airflow-k8-dbt/k8s/airflow/dags/utils/ecom_app.py ./ecom_exporter.py

CMD ["python", "ecom_exporter.py"]
