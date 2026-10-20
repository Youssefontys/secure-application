# Managed PostgreSQL on B1ms (Burstable: 1 vCPU, 2 GiB), only reachable privately (B-02).
# Encrypted on disk with a key of Azure; an own key (CMK) is only possible at creation.
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${local.unique}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = var.postgres_version
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  delegated_subnet_id           = azurerm_subnet.db.id
  private_dns_zone_id           = azurerm_private_dns_zone.db.id
  public_network_access_enabled = false

  # The owner, only for the schema job; the app logs in as notes_app (MIT-27).
  administrator_login               = "notes_owner"
  administrator_password_wo         = ephemeral.azurerm_key_vault_secret.db_password.value
  administrator_password_wo_version = var.secret_version

  tags       = local.tags
  depends_on = [azurerm_private_dns_zone_virtual_network_link.db]

  # Azure picks a zone itself; without this Terraform wants to recreate the server on a next apply.
  lifecycle {
    ignore_changes = [zone]

    # Stop already at the plan if this subscription may not create PostgreSQL here, not only after a quarter of an hour.
    precondition {
      condition     = data.azapi_resource_action.postgres_capabilities.output.value[0].restricted != "Enabled"
      error_message = "This subscription may not create PostgreSQL in ${var.location} (restricted). Choose another region with -var location=..., for example northeurope."
    }
  }
}

# Per subscription and region: may a PostgreSQL server go here? That is only in this API, not in list-skus.
data "azapi_resource_action" "postgres_capabilities" {
  type                   = "Microsoft.DBforPostgreSQL/locations@2024-08-01"
  resource_id            = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.DBforPostgreSQL/locations/${var.location}"
  action                 = "capabilities"
  method                 = "GET"
  response_export_values = ["value"]
}

# Only TLS 1.3, the best setting according to Microsoft; require_secure_transport is already on by default.
resource "azurerm_postgresql_flexible_server_configuration" "tls" {
  name      = "ssl_min_protocol_version"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "TLSv1.3"
}

resource "azurerm_postgresql_flexible_server_database" "notes" {
  name      = "notes"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
