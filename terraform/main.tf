data "azurerm_client_config" "current" {}

# A short suffix for names that must be unique worldwide (Key Vault, PostgreSQL). Not a secret.
resource "random_string" "suffix" {
  # Another region gets new names: a deleted Key Vault keeps its name for another 90 days.
  keepers = { location = var.location }
  length  = 4
  special = false
  upper   = false
}

locals {
  name   = "notes"
  unique = "${local.name}-${random_string.suffix.result}"
  tags = {
    app        = "secure-application"
    managed_by = "terraform"
  }
  # Server and database; the password comes separately through PGPASSWORD, so the addresses are no secret.
  # verify-full checks certificate and host name; Microsoft advises against require, because it does not stop a man-in-the-middle.
  db_address = "${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.notes.name}?sslmode=verify-full&sslrootcert=system"
  # The owner only for the schema job; the app logs in with a role of its own (MIT-27).
  database_url_admin = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}@${local.db_address}"
  database_url_app   = "postgresql://notes_app@${local.db_address}"
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}
