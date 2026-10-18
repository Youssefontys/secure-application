# De notitie-app op Azure: Container Apps, PostgreSQL B1ms en Key Vault.
# Versies vast, zoals requirements.txt (MIT-03); .terraform.lock.hcl legt de hashes vast.
terraform {
  # 1.11 of nieuwer voor write-only argumenten: de geheimen komen niet in plan of state.
  required_version = ">= 1.11"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.8.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.9.1"
    }
    # Voor wat azurerm niet kan: de schema-job starten (app.tf).
    azapi = {
      source  = "Azure/azapi"
      version = "2.13.0"
    }
  }

  # De state staat in de opslag van scripts/azuresetup_v2.py, versleuteld met een eigen sleutel in Key Vault.
  # Init: terraform -chdir=terraform init -backend-config=../backend.conf
  backend "azurerm" {}
}

# De subscription komt uit ARM_SUBSCRIPTION_ID of az login; niets daarvan staat in de repo.
provider "azurerm" {
  # Niet standaard geregistreerd op een nieuwe subscription; welke azurerm zelf registreert, zegt het schema niet.
  resource_providers_to_register = ["Microsoft.App", "Microsoft.DBforPostgreSQL", "Microsoft.OperationalInsights"]

  features {
    key_vault {
      # Purge protection staat aan, dus wissen kan toch niet: sleutel kwijt is notities kwijt (MC-22).
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Dezelfde login als azurerm: az login of, in een pipeline, OIDC.
provider "azapi" {}
