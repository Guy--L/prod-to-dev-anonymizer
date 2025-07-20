"""Tests for anonymizer engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from config import Config
from anonymizer_engine import AnonymizerEngine


class TestAnonymizerEngine:
    """Test anonymizer engine functionality."""
    
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
    def engine(self, config):
        """Create anonymizer engine instance."""
        with patch('anonymizer_engine.SQLMetadata'), \
             patch('anonymizer_engine.PresidioClient'):
            return AnonymizerEngine(config)
    
    def test_parse_table_name_valid(self, engine):
        """Test parsing valid table names."""
        db, schema, table = engine._parse_table_name('Portal.dbo.Users')
        assert db == 'Portal'
        assert schema == 'dbo'
        assert table == 'Users'
    
    def test_parse_table_name_invalid(self, engine):
        """Test parsing invalid table names."""
        with pytest.raises(ValueError) as exc_info:
            engine._parse_table_name('invalid.table')
        
        assert "Invalid table name format" in str(exc_info.value)
    
    @patch('pyodbc.connect')
    def test_recreate_table_in_dev(self, mock_connect, engine):
        """Test table recreation in development."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        create_script = "CREATE TABLE dbo.Users (Id INT IDENTITY(1,1), Name NVARCHAR(100))"
        
        engine._recreate_table_in_dev('Portal', 'dbo', 'Users', create_script)
        
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
    
    def test_anonymize_row_with_preserve_columns(self, engine):
        """Test row anonymization with preserved columns."""
        engine.presidio_client.anonymize_data = Mock(return_value={'name': '<PERSON>'})
        
        row_dict = {'id': 1, 'name': 'John Doe', 'status': 'active'}
        preserve_columns = {'id', 'status'}
        
        result = engine._anonymize_row(row_dict, preserve_columns)
        
        assert result['id'] == 1
        assert result['status'] == 'active'
        assert result['name'] == '<PERSON>'
        
        engine.presidio_client.anonymize_data.assert_called_once_with({'name': 'John Doe'})
    
    def test_anonymize_row_no_sensitive_data(self, engine):
        """Test row anonymization with no sensitive data."""
        row_dict = {'id': 1, 'count': 5, 'active': True}
        preserve_columns = set()
        
        result = engine._anonymize_row(row_dict, preserve_columns)
        
        assert result == row_dict
    
    @patch('pyodbc.connect')
    def test_copy_and_anonymize_data(self, mock_connect, engine):
        """Test data copying and anonymization."""
        prod_conn = Mock()
        dev_conn = Mock()
        prod_cursor = Mock()
        dev_cursor = Mock()
        
        prod_conn.cursor.return_value = prod_cursor
        dev_conn.cursor.return_value = dev_cursor
        
        prod_cursor.description = [('id',), ('name',), ('email',)]
        prod_cursor.__iter__ = Mock(return_value=iter([
            (1, 'John Doe', 'john@example.com'),
            (2, 'Jane Smith', 'jane@example.com')
        ]))
        
        mock_connect.side_effect = [
            prod_conn.__enter__.return_value,
            dev_conn.__enter__.return_value
        ]
        
        engine.presidio_client.anonymize_data = Mock(side_effect=[
            {'name': '<PERSON>', 'email': '<EMAIL>'},
            {'name': '<PERSON>', 'email': '<EMAIL>'}
        ])
        
        metadata = {
            'identity_columns': ['id'],
            'foreign_key_columns': [],
            'enum_columns': []
        }
        
        engine._copy_and_anonymize_data('Portal', 'dbo', 'Users', metadata)
        
        assert dev_cursor.executemany.called
        dev_conn.commit.assert_called()
