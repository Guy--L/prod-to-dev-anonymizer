#!/usr/bin/env python3
"""
Production to Development Data Anonymizer CLI

A command-line tool for copying database tables from production to development
while anonymizing sensitive data using Microsoft Presidio.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List

import click
from dotenv import load_dotenv

from anonymizer_engine import AnonymizerEngine
from config import Config

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_table_list(file_path: str) -> List[str]:
    """Load table list from file."""
    try:
        with open(file_path, 'r') as f:
            tables = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"Loaded {len(tables)} tables from {file_path}")
        return tables
    except FileNotFoundError:
        logger.error(f"Table list file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading table list file: {e}")
        sys.exit(1)


@click.command()
@click.argument('table_list_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(table_list_file: str, dry_run: bool, verbose: bool):
    """
    Anonymize database tables during production to development copy.
    
    TABLE_LIST_FILE: Path to file containing database.schema.table entries (one per line)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting Production to Development Data Anonymizer")
    
    try:
        config = Config()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    tables = load_table_list(table_list_file)
    
    if not tables:
        logger.warning("No tables found in the input file")
        return
    
    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        for table in tables:
            logger.info(f"Would process: {table}")
        return
    
    try:
        engine = AnonymizerEngine(config)
    except Exception as e:
        logger.error(f"Failed to initialize anonymizer engine: {e}")
        sys.exit(1)
    
    success_count = 0
    error_count = 0
    
    for table_name in tables:
        try:
            logger.info(f"Processing table: {table_name}")
            engine.process_table(table_name)
            success_count += 1
            logger.info(f"Successfully processed: {table_name}")
        except Exception as e:
            logger.error(f"Failed to process {table_name}: {e}")
            error_count += 1
    
    logger.info(f"Processing complete. Success: {success_count}, Errors: {error_count}")
    
    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
