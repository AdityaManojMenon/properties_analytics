#!/usr/bin/env python3
"""
Property Analytics Project Setup Script
Initializes the complete data infrastructure for property analytics pipeline
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PropertyAnalyticsSetup:
    """Main setup class for the property analytics project"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from environment or defaults"""
        return {
            'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'property-analytics-project'),
            'gcs_bucket': os.getenv('GCS_BUCKET', 'property-data-bucket'),
            'bigquery_dataset': os.getenv('BIGQUERY_DATASET', 'property_data'),
            'bigquery_location': os.getenv('BIGQUERY_LOCATION', 'US'),
            'slack_webhook': os.getenv('SLACK_WEBHOOK_URL', ''),
            'proxy_service': os.getenv('PROXY_SERVICE', 'local'),  # 'local', 'brightdata', 'proxymesh'
        }
    
    def create_directory_structure(self):
        """Create the complete project directory structure"""
        logger.info("Creating project directory structure...")
        
        directories = [
            'data/raw/dubai',
            'data/raw/nyc',
            'data/raw/london',
            'data/processed/dubai',
            'data/processed/nyc',
            'data/processed/london',
            'data/final',
            'notebooks/dubai',
            'notebooks/nyc',
            'notebooks/london',
            'src/scraper/scraper/spiders',
            'src/scraper/scraper/utils',
            'dags/utils',
            'dbt/models/staging',
            'dbt/models/intermediate',
            'dbt/models/marts',
            'dbt/models/analytics',
            'dbt/macros',
            'dbt/tests',
            'tableau/datasources',
            'tableau/workbooks',
            'scripts/analysis',
            'scripts/data_collection',
            'scripts/processing',
            'scripts/deployment',
            'docker',
            'terraform',
            'logs',
            'docs',
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {full_path}")
    
    def install_python_dependencies(self):
        """Install required Python packages"""
        logger.info("Installing Python dependencies...")
        
        # Core dependencies
        core_packages = [
            'scrapy>=2.8.0',
            'pandas>=1.5.0',
            'numpy>=1.21.0',
            'requests>=2.28.0',
            'beautifulsoup4>=4.11.0',
            'selenium>=4.8.0',
            'google-cloud-storage>=2.7.0',
            'google-cloud-bigquery>=3.4.0',
            'google-cloud-dataflow>=0.9.0',
            'apache-airflow>=2.5.0',
            'apache-airflow-providers-google>=10.0.0',
            'dbt-core>=1.4.0',
            'dbt-bigquery>=1.4.0',
            'great-expectations>=0.15.0',
            'sqlalchemy>=1.4.0',
            'psycopg2-binary>=2.9.0',
            'redis>=4.3.0',
            'celery>=5.2.0',
            'jupyter>=1.0.0',
            'matplotlib>=3.5.0',
            'seaborn>=0.11.0',
            'plotly>=5.13.0',
            'streamlit>=1.17.0',
            'fastapi>=0.95.0',
            'uvicorn>=0.20.0',
            'python-dotenv>=0.19.0',
            'click>=8.0.0',
            'pydantic>=1.10.0',
            'typing-extensions>=4.0.0',
        ]
        
        # Optional packages for enhanced functionality
        optional_packages = [
            'proxyscrape>=0.3.0',
            'fake-useragent>=1.1.0',
            'scrapy-rotating-proxies>=0.6.0',
            'scrapy-user-agents>=0.1.0',
            'scrapy-splash>=0.8.0',
            'scrapyd>=1.2.0',
            'scrapyd-client>=1.2.0',
            'datadog>=0.44.0',
            'sentry-sdk>=1.15.0',
            'prometheus-client>=0.15.0',
        ]
        
        # Install packages
        for package in core_packages:
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                             check=True, capture_output=True)
                logger.info(f"Installed: {package}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {package}: {e}")
    
    def create_configuration_files(self):
        """Create configuration files for all services"""
        logger.info("Creating configuration files...")
        
        # Docker Compose for local development
        self.create_docker_compose()
        
        # Airflow configuration
        self.create_airflow_config()
        
        # dbt configuration
        self.create_dbt_config()
        
        # Scrapy configuration
        self.create_scrapy_config()
        
        # Environment variables
        self.create_env_file()
        
        # Proxy configuration
        self.create_proxy_config()
        
        # BigQuery schema
        self.create_bigquery_schema()
    
    def create_docker_compose(self):
        """Create Docker Compose file for local development"""
        docker_compose = {
            'version': '3.8',
            'services': {
                'postgres': {
                    'image': 'postgres:14',
                    'environment': {
                        'POSTGRES_USER': 'airflow',
                        'POSTGRES_PASSWORD': 'airflow',
                        'POSTGRES_DB': 'airflow'
                    },
                    'volumes': ['postgres_data:/var/lib/postgresql/data'],
                    'ports': ['5432:5432']
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'ports': ['6379:6379']
                },
                'airflow-webserver': {
                    'build': '.',
                    'depends_on': ['postgres', 'redis'],
                    'environment': {
                        'AIRFLOW__CORE__EXECUTOR': 'CeleryExecutor',
                        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN': 'postgresql+psycopg2://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__RESULT_BACKEND': 'db+postgresql://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__BROKER_URL': 'redis://redis:6379/0',
                        'AIRFLOW__CORE__FERNET_KEY': '',
                        'AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION': 'true',
                        'AIRFLOW__CORE__LOAD_EXAMPLES': 'false',
                        'AIRFLOW__API__AUTH_BACKENDS': 'airflow.api.auth.backend.basic_auth'
                    },
                    'volumes': [
                        './dags:/opt/airflow/dags',
                        './logs:/opt/airflow/logs',
                        './plugins:/opt/airflow/plugins',
                        './src:/opt/airflow/src',
                        './dbt:/opt/airflow/dbt'
                    ],
                    'ports': ['8080:8080'],
                    'command': 'webserver'
                },
                'airflow-scheduler': {
                    'build': '.',
                    'depends_on': ['postgres', 'redis'],
                    'environment': {
                        'AIRFLOW__CORE__EXECUTOR': 'CeleryExecutor',
                        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN': 'postgresql+psycopg2://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__RESULT_BACKEND': 'db+postgresql://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__BROKER_URL': 'redis://redis:6379/0',
                        'AIRFLOW__CORE__FERNET_KEY': '',
                        'AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION': 'true',
                        'AIRFLOW__CORE__LOAD_EXAMPLES': 'false'
                    },
                    'volumes': [
                        './dags:/opt/airflow/dags',
                        './logs:/opt/airflow/logs',
                        './plugins:/opt/airflow/plugins',
                        './src:/opt/airflow/src',
                        './dbt:/opt/airflow/dbt'
                    ],
                    'command': 'scheduler'
                },
                'airflow-worker': {
                    'build': '.',
                    'depends_on': ['postgres', 'redis'],
                    'environment': {
                        'AIRFLOW__CORE__EXECUTOR': 'CeleryExecutor',
                        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN': 'postgresql+psycopg2://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__RESULT_BACKEND': 'db+postgresql://airflow:airflow@postgres/airflow',
                        'AIRFLOW__CELERY__BROKER_URL': 'redis://redis:6379/0',
                        'AIRFLOW__CORE__FERNET_KEY': '',
                        'AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION': 'true',
                        'AIRFLOW__CORE__LOAD_EXAMPLES': 'false'
                    },
                    'volumes': [
                        './dags:/opt/airflow/dags',
                        './logs:/opt/airflow/logs',
                        './plugins:/opt/airflow/plugins',
                        './src:/opt/airflow/src',
                        './dbt:/opt/airflow/dbt'
                    ],
                    'command': 'celery worker'
                },
                'jupyter': {
                    'image': 'jupyter/datascience-notebook:latest',
                    'ports': ['8888:8888'],
                    'volumes': ['./notebooks:/home/jovyan/work'],
                    'environment': {
                        'JUPYTER_ENABLE_LAB': 'yes'
                    }
                }
            },
            'volumes': {
                'postgres_data': {}
            }
        }
        
        with open(self.project_root / 'docker-compose.yml', 'w') as f:
            import yaml
            yaml.dump(docker_compose, f, default_flow_style=False)
        
        logger.info("Created docker-compose.yml")
    
    def create_airflow_config(self):
        """Create Airflow configuration"""
        airflow_config = """
[core]
dags_folder = /opt/airflow/dags
base_log_folder = /opt/airflow/logs
executor = CeleryExecutor
sql_alchemy_conn = postgresql+psycopg2://airflow:airflow@postgres/airflow
load_examples = False
fernet_key = 

[webserver]
default_ui_timezone = UTC
web_server_port = 8080

[scheduler]
catchup_by_default = False

[celery]
broker_url = redis://redis:6379/0
result_backend = db+postgresql://airflow:airflow@postgres/airflow

[api]
auth_backends = airflow.api.auth.backend.basic_auth
"""
        
        airflow_dir = self.project_root / 'airflow'
        airflow_dir.mkdir(exist_ok=True)
        
        with open(airflow_dir / 'airflow.cfg', 'w') as f:
            f.write(airflow_config)
        
        logger.info("Created Airflow configuration")
    
    def create_dbt_config(self):
        """Create dbt configuration"""
        dbt_config = {
            'property_analytics': {
                'target': 'dev',
                'outputs': {
                    'dev': {
                        'type': 'bigquery',
                        'method': 'service-account',
                        'project': self.config['gcp_project_id'],
                        'dataset': self.config['bigquery_dataset'],
                        'location': self.config['bigquery_location'],
                        'keyfile': '/path/to/service-account.json',
                        'threads': 4,
                        'timeout_seconds': 300,
                        'priority': 'interactive'
                    },
                    'prod': {
                        'type': 'bigquery',
                        'method': 'service-account',
                        'project': self.config['gcp_project_id'],
                        'dataset': f"{self.config['bigquery_dataset']}_prod",
                        'location': self.config['bigquery_location'],
                        'keyfile': '/path/to/service-account.json',
                        'threads': 8,
                        'timeout_seconds': 300,
                        'priority': 'batch'
                    }
                }
            }
        }
        
        dbt_dir = self.project_root / 'dbt'
        with open(dbt_dir / 'profiles.yml', 'w') as f:
            import yaml
            yaml.dump(dbt_config, f, default_flow_style=False)
        
        # Create dbt_project.yml
        dbt_project = {
            'name': 'property_analytics',
            'version': '1.0.0',
            'config-version': 2,
            'profile': 'property_analytics',
            'model-paths': ['models'],
            'analysis-paths': ['analysis'],
            'test-paths': ['tests'],
            'seed-paths': ['seeds'],
            'macro-paths': ['macros'],
            'snapshot-paths': ['snapshots'],
            'target-path': 'target',
            'clean-targets': ['target', 'dbt_packages'],
            'models': {
                'property_analytics': {
                    'staging': {
                        'materialized': 'view'
                    },
                    'intermediate': {
                        'materialized': 'table'
                    },
                    'marts': {
                        'materialized': 'table'
                    },
                    'analytics': {
                        'materialized': 'table'
                    }
                }
            }
        }
        
        with open(dbt_dir / 'dbt_project.yml', 'w') as f:
            import yaml
            yaml.dump(dbt_project, f, default_flow_style=False)
        
        logger.info("Created dbt configuration")
    
    def create_scrapy_config(self):
        """Create Scrapy configuration"""
        scrapy_settings = """
BOT_NAME = 'property_scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure delays and concurrency
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = 0.5
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Configure pipelines
ITEM_PIPELINES = {
    'scraper.pipelines.ValidationPipeline': 300,
    'scraper.pipelines.DeduplicationPipeline': 400,
    'scraper.pipelines.BigQueryPipeline': 500,
}

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
}

# User agent settings
USER_AGENT = 'property_scraper (+http://www.yourdomain.com)'

# AutoThrottle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = True

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = 'httpcache'

# Rotating proxy settings
ROTATING_PROXY_LIST_PATH = 'proxy_list.txt'
ROTATING_PROXY_CLOSE_SPIDER = True

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'scrapy.log'

# BigQuery settings
BIGQUERY_PROJECT_ID = 'property-analytics-project'
BIGQUERY_DATASET = 'property_data'
"""
        
        scrapy_dir = self.project_root / 'src' / 'scraper' / 'scraper'
        with open(scrapy_dir / 'settings.py', 'w') as f:
            f.write(scrapy_settings)
        
        logger.info("Created Scrapy configuration")
    
    def create_env_file(self):
        """Create environment variables file"""
        env_content = f"""
# Google Cloud Platform Configuration
GCP_PROJECT_ID={self.config['gcp_project_id']}
GCS_BUCKET={self.config['gcs_bucket']}
BIGQUERY_DATASET={self.config['bigquery_dataset']}
BIGQUERY_LOCATION={self.config['bigquery_location']}

# Airflow Configuration
AIRFLOW__CORE__FERNET_KEY=your_fernet_key_here
AIRFLOW__WEBSERVER__SECRET_KEY=your_secret_key_here

# External APIs
FRED_KEY=your_fred_api_key_here
OPEN_EXCHANGE_RATES_KEY=your_exchange_rates_key_here

# Proxy Configuration
PROXY_SERVICE={self.config['proxy_service']}
BRIGHTDATA_USERNAME=your_brightdata_username
BRIGHTDATA_PASSWORD=your_brightdata_password

# Notification Settings
SLACK_WEBHOOK_URL={self.config['slack_webhook']}
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_email_password

# Database Configuration
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Development Settings
DEBUG=True
ENVIRONMENT=development
"""
        
        with open(self.project_root / '.env', 'w') as f:
            f.write(env_content)
        
        logger.info("Created .env file")
    
    def create_proxy_config(self):
        """Create proxy configuration file"""
        proxy_content = """# Proxy List for Property Finder Spider
# Format options:
# host:port
# host:port:username:password
# protocol://username:password@host:port
# 
# Example entries:
# 123.456.789.10:8080
# 123.456.789.11:8080:user:pass
# http://user:pass@123.456.789.12:8080
# 
# Add your proxy servers below:
# proxy1.example.com:8080
# proxy2.example.com:8080:username:password
"""
        
        with open(self.project_root / 'proxy_list.txt', 'w') as f:
            f.write(proxy_content)
        
        logger.info("Created proxy configuration")
    
    def create_bigquery_schema(self):
        """Create BigQuery schema definitions"""
        schema_dir = self.project_root / 'scripts' / 'bigquery_schemas'
        schema_dir.mkdir(exist_ok=True)
        
        # Sales listings schema
        sales_schema = [
            {"name": "property_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "url", "type": "STRING", "mode": "REQUIRED"},
            {"name": "title", "type": "STRING"},
            {"name": "price_aed", "type": "INTEGER"},
            {"name": "price_usd", "type": "FLOAT"},
            {"name": "area_sqft", "type": "INTEGER"},
            {"name": "bedrooms", "type": "INTEGER"},
            {"name": "bathrooms", "type": "INTEGER"},
            {"name": "property_type", "type": "STRING"},
            {"name": "area_name", "type": "STRING"},
            {"name": "location", "type": "STRING"},
            {"name": "features", "type": "STRING", "mode": "REPEATED"},
            {"name": "agent_name", "type": "STRING"},
            {"name": "agency_name", "type": "STRING"},
            {"name": "scraped_at", "type": "TIMESTAMP"},
            {"name": "source", "type": "STRING"},
            {"name": "price_per_sqft_aed", "type": "FLOAT"},
            {"name": "price_per_sqft_usd", "type": "FLOAT"},
        ]
        
        with open(schema_dir / 'sales_listings.json', 'w') as f:
            json.dump(sales_schema, f, indent=2)
        
        logger.info("Created BigQuery schema definitions")
    
    def create_documentation(self):
        """Create project documentation"""
        logger.info("Creating project documentation...")
        
        readme_content = """# Property Analytics Project

A comprehensive real estate analytics platform that scrapes property listings from multiple sources, processes data through a modern data stack, and provides insights through interactive dashboards.

## Architecture Overview

- **Data Collection**: Scrapy spiders with proxy rotation
- **Orchestration**: Apache Airflow for workflow management
- **Data Processing**: dbt for data transformations
- **Storage**: Google BigQuery for analytical storage
- **Visualization**: Tableau for interactive dashboards

## Quick Start

1. **Setup Environment**
   ```bash
   python setup_project.py
   ```

2. **Start Infrastructure**
   ```bash
   docker-compose up -d
   ```

3. **Run Scrapers**
   ```bash
   cd src/scraper
   scrapy crawl property_finder -a target_count=1000
   ```

4. **Process Data**
   ```bash
   cd dbt
   dbt run
   ```

## Data Sources

- Property Finder (Dubai)
- Zillow (NYC)
- Rightmove (London)
- Economic indicators (FRED API)
- Forex rates (Open Exchange Rates)

## Key Metrics

- **Market Health**: Absorption rate, days on market, months of supply
- **Profitability**: Gross/net rental yield, cash-on-cash return
- **Risk Assessment**: Vacancy rate, price-to-rent ratio, LTV

## Project Structure

```
property_analytics/
├── src/scraper/           # Scrapy spiders
├── dags/                  # Airflow DAGs
├── dbt/                   # Data transformations
├── notebooks/             # Jupyter notebooks
├── tableau/               # Tableau workbooks
├── data/                  # Raw and processed data
├── scripts/               # Utility scripts
└── docker/                # Docker configurations
```

## Configuration

See `.env` file for environment variables and configuration options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
"""
        
        with open(self.project_root / 'README.md', 'w') as f:
            f.write(readme_content)
        
        logger.info("Created README.md")
    
    def run_setup(self):
        """Run the complete setup process"""
        logger.info("Starting Property Analytics Project Setup...")
        
        try:
            # Create project structure
            self.create_directory_structure()
            
            # Install dependencies
            self.install_python_dependencies()
            
            # Create configuration files
            self.create_configuration_files()
            
            # Create documentation
            self.create_documentation()
            
            logger.info("✅ Project setup completed successfully!")
            logger.info("Next steps:")
            logger.info("1. Update .env file with your API keys and credentials")
            logger.info("2. Add your proxy servers to proxy_list.txt")
            logger.info("3. Start the infrastructure: docker-compose up -d")
            logger.info("4. Access Airflow UI at http://localhost:8080")
            logger.info("5. Access Jupyter at http://localhost:8888")
            
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            sys.exit(1)

def main():
    """Main function"""
    setup = PropertyAnalyticsSetup()
    setup.run_setup()

if __name__ == "__main__":
    main() 