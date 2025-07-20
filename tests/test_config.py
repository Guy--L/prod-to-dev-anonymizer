"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from config import Config


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization_with_env_vars(self):
        """Test config initialization with environment variables."""
        with patch.dict(os.environ, {
            'PROD_SQL_CONNECTION': 'prod_conn_string',
            'DEV_SQL_CONNECTION': 'dev_conn_string',
            'PRESIDIO_ANALYZER_URL': 'http://analyzer.example.com',
            'PRESIDIO_ANONYMIZER_URL': 'http://anonymizer.example.com',
            'LOG_LEVEL': 'DEBUG'
        }):
            config = Config()
            
            assert config.prod_sql_connection == 'prod_conn_string'
            assert config.dev_sql_connection == 'dev_conn_string'
            assert config.presidio_analyzer_url == 'http://analyzer.example.com'
            assert config.presidio_anonymizer_url == 'http://anonymizer.example.com'
            assert config.log_level == 'DEBUG'
    
    def test_config_validation_success(self):
        """Test successful config validation."""
        with patch.dict(os.environ, {
            'PROD_SQL_CONNECTION': 'prod_conn_string',
            'DEV_SQL_CONNECTION': 'dev_conn_string',
            'PRESIDIO_ANALYZER_URL': 'http://analyzer.example.com',
            'PRESIDIO_ANONYMIZER_URL': 'http://anonymizer.example.com'
        }):
            config = Config()
            config.validate()  # Should not raise
    
    def test_config_validation_missing_fields(self):
        """Test config validation with missing fields."""
        with patch.dict(os.environ, {
            'PROD_SQL_CONNECTION': 'prod_conn_string'
        }, clear=True):
            config = Config()
            
            with pytest.raises(ValueError) as exc_info:
                config.validate()
            
            assert "Missing required environment variables" in str(exc_info.value)
    
    def test_get_connection_string(self):
        """Test connection string formatting."""
        with patch.dict(os.environ, {
            'PROD_SQL_CONNECTION': 'SERVER=prod;DATABASE={db};UID=user',
            'DEV_SQL_CONNECTION': 'SERVER=dev;DATABASE={db};UID=user',
            'PRESIDIO_ANALYZER_URL': 'http://analyzer.example.com',
            'PRESIDIO_ANONYMIZER_URL': 'http://anonymizer.example.com'
        }):
            config = Config()
            
            prod_conn = config.get_connection_string('TestDB', is_prod=True)
            dev_conn = config.get_connection_string('TestDB', is_prod=False)
            
            assert prod_conn == 'SERVER=prod;DATABASE=TestDB;UID=user'
            assert dev_conn == 'SERVER=dev;DATABASE=TestDB;UID=user'
