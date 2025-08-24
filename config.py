"""Configuration management for the anonymizer."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration settings for the anonymizer."""
    
    prod_sql_connection: str
    dev_sql_connection: str
    presidio_analyzer_url: str
    presidio_anonymizer_url: str
    log_level: str = "INFO"
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.prod_sql_connection = os.getenv('PROD_SQL_CONNECTION', '')
        self.dev_sql_connection = os.getenv('DEV_SQL_CONNECTION', '')
        self.presidio_analyzer_url = os.getenv('PRESIDIO_ANALYZER_URL', '')
        self.presidio_anonymizer_url = os.getenv('PRESIDIO_ANONYMIZER_URL', '')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    def validate(self) -> None:
        """Validate that all required configuration is present."""
        required_fields = [
            ('PROD_SQL_CONNECTION', self.prod_sql_connection),
            ('DEV_SQL_CONNECTION', self.dev_sql_connection),
            ('PRESIDIO_ANALYZER_URL', self.presidio_analyzer_url),
            ('PRESIDIO_ANONYMIZER_URL', self.presidio_anonymizer_url),
        ]
        
        missing_fields = [name for name, value in required_fields if not value]
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    def get_connection_string(self, database: str, is_prod: bool = True) -> str:
        """Get connection string with database substituted."""
        base_conn = self.prod_sql_connection if is_prod else self.dev_sql_connection
        return base_conn.format(db=database)
