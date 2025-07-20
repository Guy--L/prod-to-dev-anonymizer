@description('Main deployment template for Production to Development Data Anonymizer')
param location string = resourceGroup().location
param environment string = 'dev'
param projectName string = 'prod-to-dev-anonymizer'

@description('SQL Server connection strings')
@secure()
param sqlProdConnection string
@secure()
param sqlDevConnection string

@description('Presidio service URLs')
param presidioAnalyzerUrl string = ''
param presidioAnonymizerUrl string = ''

@description('Deploy Presidio services')
param deployPresidio bool = false

@description('Container image for the anonymizer')
param containerImage string = 'ghcr.io/listerguy/prod-to-dev-anonymizer:latest'

var resourcePrefix = '${projectName}-${environment}'
var tags = {
  Environment: environment
  Project: projectName
  Purpose: 'Data Anonymization'
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container App Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourcePrefix}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Storage Account for table lists and logs
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${resourcePrefix}storage', '-', '')
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Blob container for input files
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource inputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'input'
  properties: {
    publicAccess: 'None'
  }
}

resource outputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'output'
  properties: {
    publicAccess: 'None'
  }
}

// Presidio services (optional)
module presidio 'presidio.bicep' = if (deployPresidio) {
  name: 'presidio-deployment'
  params: {
    location: location
    environment: environment
    resourcePrefix: resourcePrefix
    tags: tags
    containerAppEnvironmentId: containerAppEnvironment.id
  }
}

// Container App Job for the anonymizer
resource anonymizerJob 'Microsoft.App/jobs@2023-05-01' = {
  name: '${resourcePrefix}-job'
  location: location
  tags: tags
  properties: {
    environmentId: containerAppEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 1
      manualTriggerConfig: {
        replicaCompletionCount: 1
        parallelism: 1
      }
      secrets: [
        {
          name: 'sql-prod-connection'
          value: sqlProdConnection
        }
        {
          name: 'sql-dev-connection'
          value: sqlDevConnection
        }
        {
          name: 'storage-connection'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'anonymizer'
          image: containerImage
          env: [
            {
              name: 'PROD_SQL_CONNECTION'
              secretRef: 'sql-prod-connection'
            }
            {
              name: 'DEV_SQL_CONNECTION'
              secretRef: 'sql-dev-connection'
            }
            {
              name: 'PRESIDIO_ANALYZER_URL'
              value: deployPresidio ? presidio.outputs.analyzerUrl : presidioAnalyzerUrl
            }
            {
              name: 'PRESIDIO_ANONYMIZER_URL'
              value: deployPresidio ? presidio.outputs.anonymizerUrl : presidioAnonymizerUrl
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          volumeMounts: [
            {
              volumeName: 'input-volume'
              mountPath: '/app/input'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'input-volume'
          storageType: 'AzureFile'
          storageName: 'input-storage'
        }
      ]
    }
  }
}

// Storage mount for input files
resource inputStorageMount 'Microsoft.App/managedEnvironments/storages@2023-05-01' = {
  parent: containerAppEnvironment
  name: 'input-storage'
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: 'input'
      accessMode: 'ReadWrite'
    }
  }
}

// File share for input
resource fileServices 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource inputFileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  parent: fileServices
  name: 'input'
  properties: {
    shareQuota: 100
  }
}

// Outputs
output containerAppJobName string = anonymizerJob.name
output storageAccountName string = storageAccount.name
output containerAppEnvironmentName string = containerAppEnvironment.name
output logAnalyticsWorkspaceName string = logAnalytics.name
output presidioAnalyzerUrl string = deployPresidio ? presidio.outputs.analyzerUrl : presidioAnalyzerUrl
output presidioAnonymizerUrl string = deployPresidio ? presidio.outputs.anonymizerUrl : presidioAnonymizerUrl
