"""Core anonymization engine for processing database tables."""

import logging
from typing import Dict, List, Set, Any, Tuple
import pyodbc

from config import Config
from sql_metadata import SQLMetadata
from presidio_client import PresidioClient

logger = logging.getLogger(__name__)


class AnonymizerEngine:
    """Main engine for anonymizing database tables."""
    
    def __init__(self, config: Config):
        """Initialize the anonymizer engine."""
        self.config = config
        self.sql_metadata = SQLMetadata(config)
        self.presidio_client = PresidioClient(config)
    
    def process_table(self, table_name: str) -> None:
        """
        Process a single table: delete from dev, recreate schema, copy and anonymize data.
        
        Args:
            table_name: Fully qualified table name (database.schema.table)
        """
        try:
            database, schema, table = self._parse_table_name(table_name)
            logger.info(f"Processing {database}.{schema}.{table}")
            
            metadata = self.sql_metadata.get_table_metadata(database, schema, table)
            
            create_script = self.sql_metadata.get_create_script(database, schema, table)
            if not create_script:
                raise ValueError(f"Could not retrieve schema for {table_name}")
            
            self._recreate_table_in_dev(database, schema, table, create_script)
            
            self._copy_and_anonymize_data(database, schema, table, metadata)
            
            logger.info(f"Successfully processed {table_name}")
            
        except Exception as e:
            logger.error(f"Error processing {table_name}: {e}")
            raise
    
    def _parse_table_name(self, table_name: str) -> Tuple[str, str, str]:
        """Parse fully qualified table name into components."""
        parts = table_name.split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid table name format. Expected 'database.schema.table', got: {table_name}")
        return parts[0], parts[1], parts[2]
    
    def _recreate_table_in_dev(self, database: str, schema: str, table: str, create_script: str) -> None:
        """Drop and recreate table in development database."""
        dev_conn_str = self.config.get_connection_string(database, is_prod=False)
        
        with pyodbc.connect(dev_conn_str) as conn:
            cursor = conn.cursor()
            
            drop_sql = f"IF OBJECT_ID('{schema}.{table}', 'U') IS NOT NULL DROP TABLE {schema}.{table}"
            logger.debug(f"Dropping table: {drop_sql}")
            cursor.execute(drop_sql)
            
            logger.debug(f"Creating table with script: {create_script[:100]}...")
            cursor.execute(create_script)
            
            conn.commit()
            logger.info(f"Recreated table {schema}.{table} in development")
    
    def _copy_and_anonymize_data(self, database: str, schema: str, table: str, metadata: Dict[str, Any]) -> None:
        """Copy data from production to development with anonymization."""
        prod_conn_str = self.config.get_connection_string(database, is_prod=True)
        dev_conn_str = self.config.get_connection_string(database, is_prod=False)
        
        preserve_columns = set()
        preserve_columns.update(metadata.get('identity_columns', []))
        preserve_columns.update(metadata.get('foreign_key_columns', []))
        preserve_columns.update(metadata.get('enum_columns', []))
        
        logger.info(f"Preserving columns: {preserve_columns}")
        
        with pyodbc.connect(prod_conn_str) as prod_conn, pyodbc.connect(dev_conn_str) as dev_conn:
            prod_cursor = prod_conn.cursor()
            select_sql = f"SELECT * FROM {schema}.{table}"
            logger.debug(f"Reading data: {select_sql}")
            prod_cursor.execute(select_sql)
            
            columns = [desc[0] for desc in prod_cursor.description]
            logger.info(f"Processing {len(columns)} columns: {columns}")
            
            dev_cursor = dev_conn.cursor()
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO {schema}.{table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            batch_size = 1000
            batch = []
            row_count = 0
            
            for row in prod_cursor:
                row_dict = dict(zip(columns, row))
                
                anonymized_row = self._anonymize_row(row_dict, preserve_columns)
                
                batch.append([anonymized_row[col] for col in columns])
                
                if len(batch) >= batch_size:
                    dev_cursor.executemany(insert_sql, batch)
                    dev_conn.commit()
                    row_count += len(batch)
                    logger.debug(f"Inserted batch of {len(batch)} rows (total: {row_count})")
                    batch = []
            
            if batch:
                dev_cursor.executemany(insert_sql, batch)
                dev_conn.commit()
                row_count += len(batch)
            
            logger.info(f"Copied and anonymized {row_count} rows")
    
    def _anonymize_row(self, row_dict: Dict[str, Any], preserve_columns: Set[str]) -> Dict[str, Any]:
        """Anonymize a single row, preserving specified columns."""
        sensitive_data = {}
        for column, value in row_dict.items():
            if column not in preserve_columns and isinstance(value, str) and value:
                sensitive_data[column] = value
        
        if not sensitive_data:
            return row_dict
        
        try:
            anonymized_data = self.presidio_client.anonymize_data(sensitive_data)
            
            result = row_dict.copy()
            result.update(anonymized_data)
            return result
            
        except Exception as e:
            logger.warning(f"Failed to anonymize row data: {e}. Using original values.")
            return row_dict
