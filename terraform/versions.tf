# The notes app on Azure: Container Apps, PostgreSQL B1ms and Key Vault.
# Versions pinned, like requirements.txt (MIT-03); .terraform.lock.hcl records the hashes.
terraform {
  # 1.11 or newer for write-only arguments: the secrets do not go into plan or state.
  required_version = ">= 1.11"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.9.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.9.1"
    }
    # For what azurerm cannot do: starting the schema job (app.tf).
    azapi = {
      source  = "Azure/azapi"
      version = "2.13.0"
    }
  }

  # The state is in the storage of scripts/setup_azure.py, encrypted with an own key in Key Vault.
  # Init: terraform -chdir=terraform init -backend-config=../backend.conf
  backend "azurerm" {}
}

# The subscription comes from ARM_SUBSCRIPTION_ID or az login; none of that is in the repo.
provider "azurerm" {
  # Not registered by default on a new subscription; the schema does not say which ones azurerm registers itself.
  # Exactly as Azure returns them: azurerm compares case, and Azure calls this one microsoft.insights.
  resource_providers_to_register = ["Microsoft.App", "Microsoft.DBforPostgreSQL", "microsoft.insights", "Microsoft.OperationalInsights"]

  features {
    key_vault {
      # Purge protection is on, so purging is not possible anyway: key lost means notes lost (MC-22).
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# The same sign-in as azurerm: az login or, in a pipeline, OIDC.
provider "azapi" {}
