output "app_url" {
  value = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

# De blokkades van de laatste dag uit de bewaarde log; de regels komen er een paar minuten na het gebeuren in.
output "security_log_command" {
  value = "az monitor log-analytics query --workspace ${azurerm_log_analytics_workspace.main.workspace_id} --analytics-query \"ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1d) and Log_s has 'lockout_started' | project TimeGenerated, Log_s\" -o table"
}

# Na de eerste apply (schema en app-rol), en na het ophogen van secret_version (wachtwoord van de app-rol).
output "schema_job_command" {
  value = "az containerapp job start --name ${azurerm_container_app_job.schema.name} --resource-group ${azurerm_resource_group.main.name}"
}
