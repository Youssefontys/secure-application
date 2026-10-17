# De geheimen van de app (A-05, A-09, A-10), met RBAC in plaats van access policies.
resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.unique}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  # Sleutel kwijt is notities kwijt (MC-22): 90 dagen terug te halen, en ook een beheerder kan niet eerder wissen.
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = local.tags
}

# Een eigen vault voor het wachtwoord van de eigenaar (A-06): de app kan hem dus niet lezen, ook niet met zijn
# identiteit (MIT-27). Microsoft raadt een vault per applicatie aan, geen rechten per geheim.
resource "azurerm_key_vault" "admin" {
  name                       = "kvdb-${local.unique}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = local.tags
}

# Wie Terraform draait, mag geheimen schrijven; de vault zelf beheren hoort niet bij deze rol.
resource "azurerm_role_assignment" "kv_operator" {
  for_each             = { main = azurerm_key_vault.main.id, admin = azurerm_key_vault.admin.id }
  scope                = each.value
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Ephemeral: Terraform maakt de waarden maar bewaart ze nergens; ze gaan alleen write-only naar Key Vault.
ephemeral "random_bytes" "data_key" {
  length = 32
}

ephemeral "random_bytes" "flask_key" {
  length = 32
}

# Azure eist drie van de vier soorten tekens; zonder leestekens hoeft het nergens ge-escapet te worden.
ephemeral "random_password" "db" {
  length      = 40
  special     = false
  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
}

# Het wachtwoord van de app-rol notities_app, met dezelfde regels.
ephemeral "random_password" "app_db" {
  length      = 40
  special     = false
  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
}

resource "azurerm_key_vault_secret" "data_key" {
  name         = "data-encryption-key"
  key_vault_id = azurerm_key_vault.main.id
  value_wo     = ephemeral.random_bytes.data_key.hex
  # Niet ophogen: een nieuwe gegevenssleutel maakt alle notities en TOTP-geheimen onleesbaar, tot v2: gebouwd is.
  value_wo_version = 1
  content_type     = "hex, 256 bits"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

resource "azurerm_key_vault_secret" "flask_key" {
  name             = "flask-secret-key"
  key_vault_id     = azurerm_key_vault.main.id
  value_wo         = ephemeral.random_bytes.flask_key.hex
  value_wo_version = var.secret_version
  content_type     = "hex, 256 bits"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

resource "azurerm_key_vault_secret" "app_db_password" {
  name             = "app-db-password"
  key_vault_id     = azurerm_key_vault.main.id
  value_wo         = ephemeral.random_password.app_db.result
  value_wo_version = var.secret_version
  content_type     = "wachtwoord, 40 tekens"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

resource "azurerm_key_vault_secret" "db_password" {
  name             = "db-password"
  key_vault_id     = azurerm_key_vault.admin.id
  value_wo         = ephemeral.random_password.db.result
  value_wo_version = var.secret_version
  content_type     = "wachtwoord, 40 tekens"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

# Het wachtwoord voor de database komt terug uit Key Vault: zo hebben vault en database altijd hetzelfde,
# ook als een eerste apply halverwege stopt.
ephemeral "azurerm_key_vault_secret" "db_password" {
  name         = azurerm_key_vault_secret.db_password.name
  key_vault_id = azurerm_key_vault.admin.id
  depends_on   = [azurerm_key_vault_secret.db_password]
}
