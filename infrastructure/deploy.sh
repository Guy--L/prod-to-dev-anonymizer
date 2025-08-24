#!/bin/bash

set -e

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
RESOURCE_GROUP_NAME="${RESOURCE_GROUP_NAME:-prod-to-dev-anonymizer-rg}"
LOCATION="${LOCATION:-eastus}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

PROD_SQL_CONNECTION="${PROD_SQL_CONNECTION}"
DEV_SQL_CONNECTION="${DEV_SQL_CONNECTION}"
PRESIDIO_ANALYZER_URL="${PRESIDIO_ANALYZER_URL:-}"
PRESIDIO_ANONYMIZER_URL="${PRESIDIO_ANONYMIZER_URL:-}"
DEPLOY_PRESIDIO="${DEPLOY_PRESIDIO:-false}"

if [ -z "$SUBSCRIPTION_ID" ]; then
    echo "Error: AZURE_SUBSCRIPTION_ID environment variable is required"
    exit 1
fi

if [ -z "$PROD_SQL_CONNECTION" ]; then
    echo "Error: PROD_SQL_CONNECTION environment variable is required"
    exit 1
fi

if [ -z "$DEV_SQL_CONNECTION" ]; then
    echo "Error: DEV_SQL_CONNECTION environment variable is required"
    exit 1
fi

if [ "$DEPLOY_PRESIDIO" = "false" ] && ([ -z "$PRESIDIO_ANALYZER_URL" ] || [ -z "$PRESIDIO_ANONYMIZER_URL" ]); then
    echo "Error: PRESIDIO_ANALYZER_URL and PRESIDIO_ANONYMIZER_URL are required when DEPLOY_PRESIDIO=false"
    exit 1
fi

echo "Starting deployment..."
echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP_NAME"
echo "Location: $LOCATION"
echo "Environment: $ENVIRONMENT"
echo "Deploy Presidio: $DEPLOY_PRESIDIO"

az account set --subscription "$SUBSCRIPTION_ID"

echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP_NAME" \
    --location "$LOCATION" \
    --tags Environment="$ENVIRONMENT" Project="prod-to-dev-anonymizer"

echo "Deploying infrastructure..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file main.bicep \
    --parameters \
        location="$LOCATION" \
        environment="$ENVIRONMENT" \
        sqlProdConnection="$PROD_SQL_CONNECTION" \
        sqlDevConnection="$DEV_SQL_CONNECTION" \
        presidioAnalyzerUrl="$PRESIDIO_ANALYZER_URL" \
        presidioAnonymizerUrl="$PRESIDIO_ANONYMIZER_URL" \
        deployPresidio="$DEPLOY_PRESIDIO"

echo "Deployment completed successfully!"

echo "Getting deployment outputs..."
CONTAINER_APP_JOB_NAME=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name main \
    --query 'properties.outputs.containerAppJobName.value' \
    --output tsv)

STORAGE_ACCOUNT_NAME=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name main \
    --query 'properties.outputs.storageAccountName.value' \
    --output tsv)

echo ""
echo "=== Deployment Summary ==="
echo "Container App Job: $CONTAINER_APP_JOB_NAME"
echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo ""
echo "To run the anonymizer:"
echo "1. Upload your tablelist.txt to the storage account file share"
echo "2. Run: az containerapp job start --name $CONTAINER_APP_JOB_NAME --resource-group $RESOURCE_GROUP_NAME"
echo ""
