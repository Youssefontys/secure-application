# Beheerde PostgreSQL op B1ms (Burstable: 1 vCPU, 2 GiB), alleen privé bereikbaar (B-02).
# Op schijf versleuteld met een sleutel van Azure; een eigen sleutel (CMK) kan alleen bij het aanmaken.
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

  # De eigenaar, alleen voor de schema-job; de app logt in als notities_app (MIT-27).
  administrator_login               = "notities"
  administrator_password_wo         = ephemeral.azurerm_key_vault_secret.db_password.value
  administrator_password_wo_version = var.secret_version

  tags       = local.tags
  depends_on = [azurerm_private_dns_zone_virtual_network_link.db]

  # Azure kiest zelf een zone; zonder dit wil Terraform de server bij een volgende apply opnieuw maken.
  lifecycle {
    ignore_changes = [zone]

    # Al bij het plan stoppen als deze subscription hier geen PostgreSQL mag maken, niet pas na een kwartier.
    precondition {
      condition     = data.azapi_resource_action.postgres_capabilities.output.value[0].restricted != "Enabled"
      error_message = "Deze subscription mag in ${var.location} geen PostgreSQL maken (restricted). Kies een andere regio met -var location=..., bijvoorbeeld northeurope."
    }
  }
}

# Per subscription en regio: mag hier een PostgreSQL-server komen? Dat staat alleen in deze API, niet in list-skus.
data "azapi_resource_action" "postgres_capabilities" {
  type                   = "Microsoft.DBforPostgreSQL/locations@2024-08-01"
  resource_id            = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.DBforPostgreSQL/locations/${var.location}"
  action                 = "capabilities"
  method                 = "GET"
  response_export_values = ["value"]
}

# Alleen TLS 1.3, de beste instelling volgens Microsoft; require_secure_transport staat standaard al aan.
resource "azurerm_postgresql_flexible_server_configuration" "tls" {
  name      = "ssl_min_protocol_version"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "TLSv1.3"
}

resource "azurerm_postgresql_flexible_server_database" "notities" {
  name      = "notities"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
