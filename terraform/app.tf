# The identity of the app: only reads the secrets in this vault, nothing else.
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.name}-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# An own identity instead of system-assigned: it already exists before the app fetches the secrets.
resource "azurerm_role_assignment" "app_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

locals {
  # Per environment variable a reference to Key Vault; the value is not in Terraform (MIT-17, MIT-18).
  app_secrets = {
    DATA_ENCRYPTION_KEY = azurerm_key_vault_secret.data_key
    FLASK_SECRET_KEY    = azurerm_key_vault_secret.flask_key
    PGPASSWORD          = azurerm_key_vault_secret.app_db_password
  }
  app_settings = merge(
    {
      DATABASE_URL = local.database_url_app
      # The root certificates of Debian, for sslrootcert=system. Needed for the own OpenSSL of psycopg-binary; with the
      # libpq of Debian (MIT-43) OpenSSL also finds them itself, but this stays until that is measured on Azure.
      SSL_CERT_FILE = "/etc/ssl/certs/ca-certificates.crt"
      # Container Apps only puts the rightmost address in X-Forwarded-For: one proxy (MC-18).
      TRUSTED_PROXIES  = "1"
      HTTPS_ONLY       = "1"
      THROTTLE_IP_MODE = var.throttle_ip_mode
    },
    var.throttle_pair_exempt_users == "" ? {} : { THROTTLE_PAIR_EXEMPT_USERS = var.throttle_pair_exempt_users },
  )
}

# Only the Consumption profile: pay per use, also in an own network.
resource "azurerm_container_app_environment" "main" {
  name                     = "cae-${local.name}"
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  infrastructure_subnet_id = azurerm_subnet.apps.id
  # Keep the log in logs.tf; without these two lines it can only be followed live.
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# HTTPS of the platform: HTTP goes to HTTPS, with TLS 1.2 or 1.3 (F-01, F-02).
resource "azurerm_container_app" "app" {
  name                         = "ca-${local.name}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags
  depends_on                   = [azurerm_role_assignment.app_secrets]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "secret" {
    for_each = local.app_secrets
    content {
      name                = secret.value.name
      key_vault_secret_id = secret.value.versionless_id
      identity            = azurerm_user_assigned_identity.app.id
    }
  }

  ingress {
    external_enabled           = true
    target_port                = 5000
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = 2

    container {
      name   = "app"
      image  = var.app_image
      cpu    = 0.25
      memory = "0.5Gi"

      dynamic "env" {
        for_each = local.app_secrets
        content {
          name        = env.key
          secret_name = env.value.name
        }
      }

      dynamic "env" {
        for_each = local.app_settings
        content {
          name  = env.key
          value = env.value
        }
      }

      readiness_probe {
        transport = "HTTP"
        port      = 5000
        path      = "/login"
      }

      liveness_probe {
        transport = "HTTP"
        port      = 5000
        path      = "/login"
      }
    }
  }
}

# The schema job logs in as the owner, so an own identity: only it reads the vault with that password.
resource "azurerm_user_assigned_identity" "schema" {
  name                = "id-${local.name}-schema"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# The admin vault entirely; from the app vault only the password of notes_app. A secret that two
# applications share is the exception for which Microsoft names rights per secret.
resource "azurerm_role_assignment" "schema_secrets" {
  for_each = {
    admin  = azurerm_key_vault.admin.id
    app_db = azurerm_key_vault_secret.app_db_password.resource_versionless_id
  }
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.schema.principal_id
}

# Loads db/schema.sql into the empty database and sets the password of notes_app; Terraform starts it itself (below).
# Starting it again is fine: the schema only if the tables are not there yet, the password every time.
# The app image, because it has psycopg and the root certificates; postgres:18 has no CA bundle.
resource "azurerm_container_app_job" "schema" {
  name                         = "caj-${local.name}-schema"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 300
  # Repeatable, so on a temporary error (rights not yet known everywhere) simply once more.
  replica_retry_limit = 2
  tags                = local.tags
  depends_on          = [azurerm_role_assignment.schema_secrets]

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.schema.id]
  }

  dynamic "secret" {
    for_each = [azurerm_key_vault_secret.db_password, azurerm_key_vault_secret.app_db_password]
    content {
      name                = secret.value.name
      key_vault_secret_id = secret.value.versionless_id
      identity            = azurerm_user_assigned_identity.schema.id
    }
  }

  template {
    container {
      name   = "schema"
      image  = var.app_image
      cpu    = 0.25
      memory = "0.5Gi"
      # One transaction: if a statement fails, nothing is left half done. sql.Literal turns the
      # password into text, never SQL.
      command = ["python", "-c", <<-PY
        import os, psycopg
        from psycopg import sql
        with psycopg.connect(os.environ["DATABASE_URL"]) as c:
            if c.execute("SELECT to_regclass('public.users')").fetchone()[0] is None:
                c.execute(os.environ["SCHEMA_SQL"])
            c.execute(sql.SQL("ALTER ROLE notes_app PASSWORD {}").format(sql.Literal(os.environ["APP_DB_PASSWORD"])))
        PY
      ]

      env {
        name        = "PGPASSWORD"
        secret_name = azurerm_key_vault_secret.db_password.name
      }
      env {
        name        = "APP_DB_PASSWORD"
        secret_name = azurerm_key_vault_secret.app_db_password.name
      }
      env {
        name  = "DATABASE_URL"
        value = local.database_url_admin
      }
      env {
        name  = "SSL_CERT_FILE"
        value = local.app_settings.SSL_CERT_FILE
      }
      env {
        name  = "SCHEMA_SQL"
        value = file("${path.module}/../db/schema.sql")
      }
    }
  }
}

# When the job must run: after the first apply, and again on another schema or a new password of notes_app.
resource "terraform_data" "schema_inputs" {
  input = [filesha256("${path.module}/../db/schema.sql"), var.secret_version]
}

# Start the job; azurerm cannot do that, azapi makes the same call as az containerapp job start. The start does not wait
# until the job is done: in the first minute after a new database, logging in can still fail.
resource "azapi_resource_action" "schema_start" {
  type        = "Microsoft.App/jobs@2025-07-01"
  resource_id = azurerm_container_app_job.schema.id
  action      = "start"
  method      = "POST"

  lifecycle {
    replace_triggered_by = [terraform_data.schema_inputs]
  }
}
