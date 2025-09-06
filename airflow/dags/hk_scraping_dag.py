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
    "hk_scraping_dag",
    default_args=default_args,
    description="Daily scrape for Hong Kong rentals and sales",
    schedule_interval=None,  # tasks scheduled individually
    start_date=datetime(2025, 9, 6),
    catchup=False,
    tags=["scraping", "hongkong"],
) as dag:

    # Rentals at 10 PM EST (03:00 UTC)
    scrape_hk_rentals = BashOperator(
        task_id="scrape_hk_rentals",
        bash_command=(
            "TZ=America/New_York "
            "date && "
            "bash /Users/am/Desktop/properties_analytics/scripts/scraping/run_hk_rentals.sh"
        ),
        execution_timeout=timedelta(hours=2),
        start_date=datetime(2025, 9, 5, 22, 0),  # Starts at sept 5th 2025 at 10 PM EST
    )

    # Sales at 4 AM EST (09:00 UTC)
    scrape_hk_sales = BashOperator(
        task_id="scrape_hk_sales",
        bash_command=(
            "TZ=America/New_York "
            "date && "
            "bash /Users/am/Desktop/properties_analytics/scripts/scraping/run_hk_sales.sh"
        ),
        execution_timeout=timedelta(hours=2),
        start_date=datetime(2025, 9, 6, 4, 0),  # Starts at sept 6th 2025 at 4 AM EST
    )

    scrape_hk_rentals >> scrape_hk_sales
