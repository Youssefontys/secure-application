output "app_url" {
  value = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

# The lockouts of the last day from the kept log; the lines arrive a few minutes after they happen.
output "security_log_command" {
  value = "az monitor log-analytics query --workspace ${azurerm_log_analytics_workspace.main.workspace_id} --analytics-query \"ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1d) and Log_s has 'lockout_started' | project TimeGenerated, Log_s\" -o table"
}

# Terraform starts the job itself (app.tf); starting it again by hand is possible with this, if that is ever needed.
output "schema_job_command" {
  value = "az containerapp job start --name ${azurerm_container_app_job.schema.name} --resource-group ${azurerm_resource_group.main.name}"
}
