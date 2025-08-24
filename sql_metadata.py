"""SQL Server metadata extraction and DDL generation."""

import logging
from typing import Dict, List, Any, Optional
import pyodbc

from config import Config

logger = logging.getLogger(__name__)


class SQLMetadata:
    """Handles SQL Server metadata extraction and schema operations."""
    
    def __init__(self, config: Config):
        """Initialize SQL metadata handler."""
        self.config = config
    
    def get_table_metadata(self, database: str, schema: str, table: str) -> Dict[str, Any]:
        """Get comprehensive metadata for a table."""
        conn_str = self.config.get_connection_string(database, is_prod=True)
        
        with pyodbc.connect(conn_str) as conn:
            metadata = {
                'identity_columns': self._get_identity_columns(conn, schema, table),
                'foreign_key_columns': self._get_foreign_key_columns(conn, schema, table),
                'enum_columns': self._detect_enum_columns(conn, schema, table),
                'columns': self._get_column_info(conn, schema, table)
            }
        
        logger.debug(f"Table metadata for {schema}.{table}: {metadata}")
        return metadata
    
    def get_create_script(self, database: str, schema: str, table: str) -> Optional[str]:
        """Get CREATE TABLE script for the specified table."""
        conn_str = self.config.get_connection_string(database, is_prod=True)
        
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            script_parts = []
            
            script_parts.append(f"CREATE TABLE {schema}.{table} (")
            
            column_defs = self._get_column_definitions(cursor, schema, table)
            script_parts.append(",\n    ".join(column_defs))
            
            constraints = self._get_table_constraints(cursor, schema, table)
            if constraints:
                script_parts.append(",\n    " + ",\n    ".join(constraints))
            
            script_parts.append("\n)")
            
            return "".join(script_parts)
    
    def _get_identity_columns(self, conn: pyodbc.Connection, schema: str, table: str) -> List[str]:
        """Get list of identity columns."""
        cursor = conn.cursor()
        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        AND COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), COLUMN_NAME, 'IsIdentity') = 1
        """
        cursor.execute(query, schema, table)
        return [row[0] for row in cursor.fetchall()]
    
    def _get_foreign_key_columns(self, conn: pyodbc.Connection, schema: str, table: str) -> List[str]:
        """Get list of foreign key columns."""
        cursor = conn.cursor()
        query = """
        SELECT DISTINCT kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
            ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = ? AND kcu.TABLE_NAME = ?
        """
        cursor.execute(query, schema, table)
        return [row[0] for row in cursor.fetchall()]
    
    def _detect_enum_columns(self, conn: pyodbc.Connection, schema: str, table: str) -> List[str]:
        """Detect columns that appear to be enums (small number of distinct values)."""
        cursor = conn.cursor()
        
        string_columns_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        AND DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
        AND CHARACTER_MAXIMUM_LENGTH <= 50
        """
        cursor.execute(string_columns_query, schema, table)
        string_columns = [row[0] for row in cursor.fetchall()]
        
        enum_columns = []
        
        for column in string_columns:
            distinct_query = f"""
            SELECT COUNT(DISTINCT {column}) as distinct_count,
                   COUNT(*) as total_count
            FROM {schema}.{table}
            WHERE {column} IS NOT NULL
            """
            try:
                cursor.execute(distinct_query)
                result = cursor.fetchone()
                if result:
                    distinct_count, total_count = result
                    if total_count > 0 and (distinct_count <= 20 or distinct_count / total_count < 0.1):
                        enum_columns.append(column)
                        logger.debug(f"Column {column} detected as enum: {distinct_count} distinct values out of {total_count}")
            except Exception as e:
                logger.warning(f"Could not analyze column {column} for enum detection: {e}")
        
        return enum_columns
    
    def _get_column_info(self, conn: pyodbc.Connection, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get detailed column information."""
        cursor = conn.cursor()
        query = """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
               CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, schema, table)
        
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'name': row[0],
                'data_type': row[1],
                'is_nullable': row[2] == 'YES',
                'default': row[3],
                'max_length': row[4],
                'precision': row[5],
                'scale': row[6]
            })
        
        return columns
    
    def _get_column_definitions(self, cursor: pyodbc.Cursor, schema: str, table: str) -> List[str]:
        """Get column definitions for CREATE TABLE statement."""
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, schema, table)
        
        column_defs = []
        for row in cursor.fetchall():
            name, data_type, max_length, precision, scale, is_nullable, default, is_identity = row
            
            col_def = f"{name} {data_type}"
            
            if data_type.lower() in ('varchar', 'nvarchar', 'char', 'nchar'):
                if max_length == -1:
                    col_def += "(MAX)"
                else:
                    col_def += f"({max_length})"
            elif data_type.lower() in ('decimal', 'numeric'):
                col_def += f"({precision},{scale})"
            
            if is_identity:
                col_def += " IDENTITY(1,1)"
            
            if is_nullable == 'NO':
                col_def += " NOT NULL"
            
            if default:
                col_def += f" DEFAULT {default}"
            
            column_defs.append(col_def)
        
        return column_defs
    
    def _get_table_constraints(self, cursor: pyodbc.Cursor, schema: str, table: str) -> List[str]:
        """Get table constraints (primary keys, etc.)."""
        constraints = []
        
        pk_query = """
        SELECT kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ?
        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ORDER BY kcu.ORDINAL_POSITION
        """
        cursor.execute(pk_query, schema, table)
        pk_columns = [row[0] for row in cursor.fetchall()]
        
        if pk_columns:
            constraints.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
        
        return constraints
