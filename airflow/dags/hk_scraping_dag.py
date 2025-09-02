from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'aditya',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'hk_scraping_dag',
    default_args=default_args,
    description='Daily scrape for Hong Kong rentals',
    schedule_interval='0 9 * * *',  # 9 AM daily
    start_date=datetime(2025, 9, 2),
    catchup=False,
    tags=['scraping', 'hongkong'],
) as dag:

    scrape_hk_rentals = BashOperator(
        task_id='scrape_hk_rentals',
        bash_command='bash /Users/am/Desktop/properties_analytics/scripts/scraping/Hk_scraping/run_hk_rentals.sh ',
    )
