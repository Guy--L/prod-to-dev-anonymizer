@description('Presidio analyzer and anonymizer services deployment')
param location string
param environment string
param resourcePrefix string
param tags object
param containerAppEnvironmentId string

// App Service Plan for Presidio services
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${resourcePrefix}-presidio-plan'
  location: location
  tags: tags
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Presidio Analyzer Web App
resource presidioAnalyzer 'Microsoft.Web/sites@2023-01-01' = {
  name: '${resourcePrefix}-analyzer'
  location: location
  tags: tags
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/presidio-analyzer:latest'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://mcr.microsoft.com'
        }
        {
          name: 'WEBSITES_PORT'
          value: '3000'
        }
      ]
      httpLoggingEnabled: true
      logsDirectorySizeLimit: 35
      detailedErrorLoggingEnabled: true
    }
    httpsOnly: true
  }
}

// Presidio Anonymizer Web App
resource presidioAnonymizer 'Microsoft.Web/sites@2023-01-01' = {
  name: '${resourcePrefix}-anonymizer'
  location: location
  tags: tags
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/presidio-anonymizer:latest'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://mcr.microsoft.com'
        }
        {
          name: 'WEBSITES_PORT'
          value: '3001'
        }
      ]
      httpLoggingEnabled: true
      logsDirectorySizeLimit: 35
      detailedErrorLoggingEnabled: true
    }
    httpsOnly: true
  }
}

// Outputs
output analyzerUrl string = 'https://${presidioAnalyzer.properties.defaultHostName}'
output anonymizerUrl string = 'https://${presidioAnonymizer.properties.defaultHostName}'
output appServicePlanName string = appServicePlan.name
