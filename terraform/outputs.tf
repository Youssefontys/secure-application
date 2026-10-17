output "app_url" {
  value = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

# Eén keer na de eerste apply, om db/schema.sql te laden.
output "schema_job_command" {
  value = "az containerapp job start --name ${azurerm_container_app_job.schema.name} --resource-group ${azurerm_resource_group.main.name}"
}
