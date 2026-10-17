# De identiteit van de app: leest alleen de geheimen in deze vault, verder niets.
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.name}-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# Eigen identiteit in plaats van systeem-toegewezen: die bestaat al voordat de app de geheimen ophaalt.
resource "azurerm_role_assignment" "app_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

locals {
  # Per omgevingsvariabele een verwijzing naar Key Vault; de waarde staat niet in Terraform (MIT-17, MIT-18).
  app_secrets = {
    DATA_ENCRYPTION_KEY = azurerm_key_vault_secret.data_key
    FLASK_SECRET_KEY    = azurerm_key_vault_secret.flask_key
    PGPASSWORD          = azurerm_key_vault_secret.app_db_password
  }
  app_settings = merge(
    {
      DATABASE_URL = local.database_url_app
      # De OpenSSL in psycopg vindt zo de rootcertificaten van Debian, voor sslrootcert=system.
      SSL_CERT_FILE = "/etc/ssl/certs/ca-certificates.crt"
      # Container Apps zet alleen het meest rechtse adres in X-Forwarded-For: één proxy (MC-18).
      TRUSTED_PROXIES  = "1"
      HTTPS_ONLY       = "1"
      THROTTLE_IP_MODE = var.throttle_ip_mode
    },
    var.throttle_pair_exempt_users == "" ? {} : { THROTTLE_PAIR_EXEMPT_USERS = var.throttle_pair_exempt_users },
  )
}

# Alleen het Consumption-profiel: betalen per gebruik, ook in een eigen netwerk.
# Logs zijn alleen live te volgen; bewaren komt bij Logging en monitoring.
resource "azurerm_container_app_environment" "main" {
  name                     = "cae-${local.name}"
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  infrastructure_subnet_id = azurerm_subnet.apps.id
  tags                     = local.tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# HTTPS van het platform: HTTP gaat naar HTTPS, met TLS 1.2 of 1.3 (F-01, F-02).
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

# De schema-job logt in als eigenaar, dus een eigen identiteit: alleen die leest de vault met dat wachtwoord.
resource "azurerm_user_assigned_identity" "schema" {
  name                = "id-${local.name}-schema"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# De admin-vault helemaal; uit de app-vault alleen het wachtwoord van notities_app. Een geheim dat twee
# applicaties delen is de uitzondering waarvoor Microsoft rechten per geheim noemt.
resource "azurerm_role_assignment" "schema_secrets" {
  for_each = {
    admin  = azurerm_key_vault.admin.id
    app_db = azurerm_key_vault_secret.app_db_password.resource_versionless_id
  }
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.schema.principal_id
}

# Laadt db/schema.sql in de lege database en zet het wachtwoord van notities_app; handmatig starten (zie outputs).
# Opnieuw starten mag: het schema alleen als de tabellen er nog niet zijn, het wachtwoord elke keer.
# De app-image, want die heeft psycopg en de rootcertificaten; postgres:18 heeft geen CA-bundel.
resource "azurerm_container_app_job" "schema" {
  name                         = "caj-${local.name}-schema"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 300
  replica_retry_limit          = 0
  tags                         = local.tags
  depends_on                   = [azurerm_role_assignment.schema_secrets]

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
      # Eén transactie: lukt een statement niet, dan staat er niets half. sql.Literal maakt van het
      # wachtwoord tekst, nooit SQL.
      command = ["python", "-c", <<-PY
        import os, psycopg
        from psycopg import sql
        with psycopg.connect(os.environ["DATABASE_URL"]) as c:
            if c.execute("SELECT to_regclass('public.users')").fetchone()[0] is None:
                c.execute(os.environ["SCHEMA_SQL"])
            c.execute(sql.SQL("ALTER ROLE notities_app PASSWORD {}").format(sql.Literal(os.environ["APP_DB_PASSWORD"])))
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
