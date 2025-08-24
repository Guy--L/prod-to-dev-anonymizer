"""Tests for Presidio client."""

import pytest
from unittest.mock import Mock, patch
import requests

from config import Config
from presidio_client import PresidioClient


class TestPresidioClient:
    """Test Presidio client functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with patch.dict('os.environ', {
            'PROD_SQL_CONNECTION': 'prod_conn',
            'DEV_SQL_CONNECTION': 'dev_conn',
            'PRESIDIO_ANALYZER_URL': 'http://analyzer.example.com',
            'PRESIDIO_ANONYMIZER_URL': 'http://anonymizer.example.com'
        }):
            return Config()
    
    @pytest.fixture
    def presidio_client(self, config):
        """Create Presidio client instance."""
        return PresidioClient(config)
    
    def test_initialization(self, presidio_client):
        """Test client initialization."""
        assert presidio_client.analyzer_url == 'http://analyzer.example.com'
        assert presidio_client.anonymizer_url == 'http://anonymizer.example.com'
        assert 'PERSON' in presidio_client.anonymization_config
    
    @patch('requests.post')
    def test_analyze_text_success(self, mock_post, presidio_client):
        """Test successful text analysis."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'entity_type': 'PERSON',
                'start': 0,
                'end': 8,
                'score': 0.85
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = presidio_client._analyze_text('John Doe')
        
        assert len(result) == 1
        assert result[0]['entity_type'] == 'PERSON'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_anonymize_with_results_success(self, mock_post, presidio_client):
        """Test successful anonymization with results."""
        mock_response = Mock()
        mock_response.json.return_value = {'text': '<PERSON>'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        analysis_results = [{'entity_type': 'PERSON', 'start': 0, 'end': 8}]
        result = presidio_client._anonymize_with_results('John Doe', analysis_results)
        
        assert result == '<PERSON>'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_anonymize_data_success(self, mock_post, presidio_client):
        """Test successful data anonymization."""
        analyze_response = Mock()
        analyze_response.json.return_value = [
            {'entity_type': 'PERSON', 'start': 0, 'end': 8}
        ]
        analyze_response.raise_for_status.return_value = None
        
        anonymize_response = Mock()
        anonymize_response.json.return_value = {'text': '<PERSON>'}
        anonymize_response.raise_for_status.return_value = None
        
        mock_post.side_effect = [analyze_response, anonymize_response]
        
        data = {'name': 'John Doe', 'id': '123'}
        result = presidio_client.anonymize_data(data)
        
        assert result['name'] == '<PERSON>'
        assert result['id'] == '123'  # Non-string values should be preserved
    
    def test_anonymize_data_empty_input(self, presidio_client):
        """Test anonymization with empty input."""
        result = presidio_client.anonymize_data({})
        assert result == {}
        
        result = presidio_client.anonymize_data({'key': ''})
        assert result == {'key': ''}
    
    @patch('requests.get')
    def test_connection_success(self, mock_get, presidio_client):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = presidio_client.test_connection()
        assert result is True
        assert mock_get.call_count == 2  # Both analyzer and anonymizer
    
    @patch('requests.get')
    def test_connection_failure(self, mock_get, presidio_client):
        """Test connection failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = presidio_client.test_connection()
        assert result is False
