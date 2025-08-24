"""Client for Microsoft Presidio anonymization service."""

import json
import logging
from typing import Dict, Any, List
import requests

from config import Config

logger = logging.getLogger(__name__)


class PresidioClient:
    """Client for interacting with Presidio analyzer and anonymizer services."""
    
    def __init__(self, config: Config):
        """Initialize Presidio client."""
        self.config = config
        self.analyzer_url = config.presidio_analyzer_url.rstrip('/')
        self.anonymizer_url = config.presidio_anonymizer_url.rstrip('/')
        
        self.anonymization_config = {
            "PERSON": {"type": "replace", "new_value": "<PERSON>"},
            "EMAIL_ADDRESS": {"type": "replace", "new_value": "<EMAIL>"},
            "PHONE_NUMBER": {"type": "replace", "new_value": "<PHONE>"},
            "CREDIT_CARD": {"type": "replace", "new_value": "<CREDIT_CARD>"},
            "US_SSN": {"type": "replace", "new_value": "<SSN>"},
            "DATE_TIME": {"type": "replace", "new_value": "<DATE>"},
            "IP_ADDRESS": {"type": "replace", "new_value": "<IP_ADDRESS>"},
            "LOCATION": {"type": "replace", "new_value": "<LOCATION>"},
            "URL": {"type": "replace", "new_value": "<URL>"}
        }
    
    def anonymize_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Anonymize a dictionary of string data using Presidio.
        
        Args:
            data: Dictionary of column_name -> value pairs to anonymize
            
        Returns:
            Dictionary with anonymized values
        """
        if not data:
            return data
        
        result = {}
        
        for column, value in data.items():
            if not isinstance(value, str) or not value.strip():
                result[column] = value
                continue
            
            try:
                anonymized_value = self._anonymize_text(value)
                result[column] = anonymized_value
                
                if anonymized_value != value:
                    logger.debug(f"Anonymized {column}: '{value}' -> '{anonymized_value}'")
                
            except Exception as e:
                logger.warning(f"Failed to anonymize {column}: {e}. Using original value.")
                result[column] = value
        
        return result
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize a single text value using Presidio."""
        try:
            analysis_results = self._analyze_text(text)
            
            if not analysis_results:
                return text
            
            anonymized_text = self._anonymize_with_results(text, analysis_results)
            return anonymized_text
            
        except Exception as e:
            logger.error(f"Error in Presidio anonymization: {e}")
            raise
    
    def _analyze_text(self, text: str) -> List[Dict[str, Any]]:
        """Analyze text using Presidio analyzer."""
        analyze_url = f"{self.analyzer_url}/analyze"
        
        payload = {
            "text": text,
            "language": "en",
            "score_threshold": 0.35
        }
        
        try:
            response = requests.post(
                analyze_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            results = response.json()
            logger.debug(f"Analysis results for '{text[:50]}...': {len(results)} entities found")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to analyze text with Presidio: {e}")
            raise
    
    def _anonymize_with_results(self, text: str, analysis_results: List[Dict[str, Any]]) -> str:
        """Anonymize text using analysis results."""
        anonymize_url = f"{self.anonymizer_url}/anonymize"
        
        anonymizers = {}
        for result in analysis_results:
            entity_type = result.get("entity_type")
            if entity_type in self.anonymization_config:
                anonymizers[entity_type] = self.anonymization_config[entity_type]
        
        payload = {
            "text": text,
            "analyzer_results": analysis_results,
            "anonymizers": anonymizers
        }
        
        try:
            response = requests.post(
                anonymize_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            anonymized_text = result.get("text", text)
            
            return anonymized_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to anonymize text with Presidio: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Presidio services."""
        try:
            analyzer_health_url = f"{self.analyzer_url}/health"
            analyzer_response = requests.get(analyzer_health_url, timeout=10)
            analyzer_ok = analyzer_response.status_code == 200
            
            anonymizer_health_url = f"{self.anonymizer_url}/health"
            anonymizer_response = requests.get(anonymizer_health_url, timeout=10)
            anonymizer_ok = anonymizer_response.status_code == 200
            
            if analyzer_ok and anonymizer_ok:
                logger.info("Successfully connected to Presidio services")
                return True
            else:
                logger.error(f"Presidio connection failed. Analyzer: {analyzer_ok}, Anonymizer: {anonymizer_ok}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to test Presidio connection: {e}")
            return False
