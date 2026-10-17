data "azurerm_client_config" "current" {}

# Een kort achtervoegsel voor namen die wereldwijd uniek moeten zijn (Key Vault, PostgreSQL). Geen geheim.
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

locals {
  name   = "notities-${var.environment}"
  unique = "${local.name}-${random_string.suffix.result}"
  tags = {
    app      = "secure-application"
    omgeving = var.environment
    beheer   = "terraform"
  }
  # Gebruiker, server en database; het wachtwoord komt los via PGPASSWORD, dus dit is geen geheim.
  # verify-full controleert certificaat en hostnaam; Microsoft raadt require af, want dat houdt geen man-in-the-middle tegen.
  database_url = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.notities.name}?sslmode=verify-full&sslrootcert=system"
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}
