from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "aditya",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=15),
}

with DAG(
    "chicago_scraping_dag",
    default_args=default_args,
    description="Scrape Chicago rentals and sales",
    schedule_interval=None,  # each task scheduled separately
    start_date=datetime(2025, 9, 6),
    catchup=False,
    tags=["scraping", "chicago"],
) as dag:

    # Rentals at 10 PM EST (03:00 UTC next day)
    scrape_chicago_rentals = BashOperator(
        task_id="scrape_chicago_rentals",
        bash_command=(
            "TZ=America/New_York date && "
            "bash /Users/am/Desktop/properties_analytics/scripts/scraping/run_chicago_rentals.sh"
        ),
        execution_timeout=timedelta(hours=3),
        start_date=datetime(2025, 9, 6, 22, 0),  # 10 PM EST
    )

    # Sales at 4 AM EST (09:00 UTC)
    scrape_chicago_sales = BashOperator(
        task_id="scrape_chicago_sales",
        bash_command=(
            "TZ=America/New_York date && "
            "bash /Users/am/Desktop/properties_analytics/scripts/scraping/run_chicago_sales.sh"
        ),
        execution_timeout=timedelta(hours=3),
        start_date=datetime(2025, 9, 7, 4, 0),  # 4 AM EST
    )

    scrape_chicago_rentals >> scrape_chicago_sales
