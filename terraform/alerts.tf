# Een mail bij een blokkade (MIT-37, MC-28): de log bewaren is niet genoeg, iemand moet het ook zien.
resource "azurerm_monitor_action_group" "security" {
  name                = "ag-${local.name}-security"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "notities"
  tags                = local.tags

  email_receiver {
    name                    = "beheerder"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

# Elke 5 minuten (€1,32 per maand): een regel staat pas na een paar minuten in Log Analytics, dus vaker kijken scheelt weinig.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "lockout" {
  name                 = "alert-${local.name}-lockout"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  scopes               = [azurerm_log_analytics_workspace.main.id]
  description          = "Een teller van de poginglimieten ging op slot (lockout_started, MIT-10)."
  severity             = 2
  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"
  # Tijdens één aanval niet elke 5 minuten opnieuw mailen.
  mute_actions_after_alert_duration = "PT1H"
  # In een nieuwe workspace bestaat de tabel pas na de eerste logregel; anders weigert Azure de regel bij het aanmaken.
  skip_query_validation = true
  tags                  = local.tags

  # Een eigen identiteit, zoals Microsoft aanraadt; zonder leest de regel met de rechten van wie hem het laatst wijzigde.
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

# Alleen lezen in deze ene workspace.
resource "azurerm_role_assignment" "alert_reader" {
  scope                = azurerm_log_analytics_workspace.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azurerm_monitor_scheduled_query_rules_alert_v2.lockout.identity[0].principal_id
}
