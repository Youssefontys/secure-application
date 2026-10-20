# A mail on a lockout (MIT-37, MC-28): keeping the log is not enough, someone must also see it.
resource "azurerm_monitor_action_group" "security" {
  name                = "ag-${local.name}-security"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "notes"
  tags                = local.tags

  email_receiver {
    name                    = "admin"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

# Every 5 minutes (€1.32 per month): a line only shows up in Log Analytics after a few minutes, so looking more often helps little.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "lockout" {
  name                 = "alert-${local.name}-lockout"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  scopes               = [azurerm_log_analytics_workspace.main.id]
  description          = "A counter of the attempt limits was locked (lockout_started, MIT-10)."
  severity             = 2
  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"
  # Do not mail again every 5 minutes during one attack.
  mute_actions_after_alert_duration = "PT1H"
  # In a new workspace the table only exists after the first log line; otherwise Azure refuses the rule at creation.
  skip_query_validation = true
  tags                  = local.tags

  # An own identity, as Microsoft recommends; without it the rule reads with the rights of whoever changed it last.
  identity {
    type = "SystemAssigned"
  }

  criteria {
    query                   = "ContainerAppConsoleLogs_CL | where Log_s has \"lockout_started\""
    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0
  }

  action {
    action_groups = [azurerm_monitor_action_group.security.id]
  }
}

# Only reading in this one workspace.
resource "azurerm_role_assignment" "alert_reader" {
  scope                = azurerm_log_analytics_workspace.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azurerm_monitor_scheduled_query_rules_alert_v2.lockout.identity[0].principal_id
}
