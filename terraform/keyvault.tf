# The secrets of the app (A-05, A-09, A-10), with RBAC instead of access policies.
resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.unique}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  # Key lost means notes lost (MC-22): 90 days to recover, and not even an administrator can purge earlier.
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = local.tags
}

# A vault of its own for the password of the owner (A-06): so the app cannot read it, not even with its
# identity (MIT-27). Microsoft recommends a vault per application, not rights per secret.
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

# Whoever runs Terraform may write secrets; managing the vault itself is not part of this role.
resource "azurerm_role_assignment" "kv_operator" {
  for_each             = { main = azurerm_key_vault.main.id, admin = azurerm_key_vault.admin.id }
  scope                = each.value
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Ephemeral: Terraform makes the values but stores them nowhere; they only go write-only to Key Vault.
ephemeral "random_bytes" "data_key" {
  length = 32
}

ephemeral "random_bytes" "flask_key" {
  length = 32
}

# Azure requires three of the four kinds of characters; without punctuation it never needs escaping.
ephemeral "random_password" "db" {
  length      = 40
  special     = false
  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
}

# The password of the app role notes_app, with the same rules.
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
  # Do not raise: a new data key makes all notes and TOTP secrets unreadable, until v2: is built.
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
  content_type     = "password, 40 characters"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

resource "azurerm_key_vault_secret" "db_password" {
  name             = "db-password"
  key_vault_id     = azurerm_key_vault.admin.id
  value_wo         = ephemeral.random_password.db.result
  value_wo_version = var.secret_version
  content_type     = "password, 40 characters"
  depends_on       = [azurerm_role_assignment.kv_operator]
}

# The password for the database comes back from Key Vault: this way vault and database always have the same one,
# even if a first apply stops halfway.
ephemeral "azurerm_key_vault_secret" "db_password" {
  name         = azurerm_key_vault_secret.db_password.name
  key_vault_id = azurerm_key_vault.admin.id
  depends_on   = [azurerm_key_vault_secret.db_password]
}
