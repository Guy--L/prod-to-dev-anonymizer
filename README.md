# Production to Development Data Anonymizer

A CLI tool for copying database tables from production to development environments while anonymizing sensitive data using Microsoft Presidio. The tool preserves identity columns, foreign keys, and enum values to maintain referential integrity.

## Features

- **Selective Anonymization**: Uses Microsoft Presidio to detect and anonymize PII while preserving critical data relationships
- **Schema Preservation**: Recreates tables in development using production schema
- **Referential Integrity**: Maintains identity columns, foreign keys, and enum values
- **Azure Integration**: Deployable as Azure Container App Job with Bicep templates
- **CLI Interface**: Simple command-line interface accepting database.table lists

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure connection strings in environment variables:
```bash
export PROD_SQL_CONNECTION="DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE={db};UID=user;PWD=password"
export DEV_SQL_CONNECTION="DRIVER={ODBC Driver 17 for SQL Server};SERVER=dev-server;DATABASE={db};UID=user;PWD=password"
export PRESIDIO_ANALYZER_URL="https://your-presidio-analyzer.azurewebsites.net"
export PRESIDIO_ANONYMIZER_URL="https://your-presidio-anonymizer.azurewebsites.net"
```

3. Create a table list file:
```
Portal.dbo.ContactImport
Portal.dbo.Customer
Portal.dbo.Note
```

4. Run the anonymizer:
```bash
python main.py tablelist.txt
```

### Azure Deployment

Deploy the complete infrastructure using Bicep:

```bash
az deployment sub create \
  --location eastus \
  --template-file infrastructure/main.bicep \
  --parameters environment=dev \
               sqlProdConn="..." \
               sqlDevConn="..." \
               presidioAnalyzerUrl="..." \
               presidioAnonymizerUrl="..."
```

## Architecture

The system consists of:

1. **CLI Tool** (`main.py`): Entry point that processes table lists
2. **Anonymizer Engine** (`anonymizer_engine.py`): Core logic for table processing
3. **SQL Metadata** (`sql_metadata.py`): Schema analysis and DDL generation
4. **Presidio Client** (`presidio_client.py`): PII detection and anonymization
5. **Azure Infrastructure** (`infrastructure/`): Bicep templates for deployment

## How It Works

For each table in the input list:

1. **Schema Analysis**: Identifies identity columns, foreign keys, and enum-like fields
2. **Table Recreation**: Drops and recreates the table in development using production schema
3. **Data Processing**: Copies data row by row, applying Presidio anonymization to sensitive fields
4. **Integrity Preservation**: Maintains original values for IDs, foreign keys, and categorical data

## Configuration

### Environment Variables

- `PROD_SQL_CONNECTION`: Production database connection string
- `DEV_SQL_CONNECTION`: Development database connection string
- `PRESIDIO_ANALYZER_URL`: Presidio analyzer service endpoint
- `PRESIDIO_ANONYMIZER_URL`: Presidio anonymizer service endpoint
- `LOG_LEVEL`: Logging level (default: INFO)

### Table List Format

Each line should contain a fully qualified table name:
```
DatabaseName.SchemaName.TableName
```

Example:
```
Portal.dbo.ContactImport
Portal.dbo.Customer
Portal.dbo.Note
Portal.dbo.Address
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Building Docker Image

```bash
docker build -t prod-to-dev-anonymizer .
```

### Local Testing with Docker

```bash
docker run -v $(pwd)/tablelist.txt:/app/tablelist.txt \
  -e PROD_SQL_CONNECTION="..." \
  -e DEV_SQL_CONNECTION="..." \
  -e PRESIDIO_ANALYZER_URL="..." \
  -e PRESIDIO_ANONYMIZER_URL="..." \
  prod-to-dev-anonymizer
```

## License

MIT License - see LICENSE file for details.
