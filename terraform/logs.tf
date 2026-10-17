# De security-log (MIT-31) bewaard op Azure: Container Apps zet stdout en stderr van de app in deze workspace (MC-28).
# Daar kan de app zelf niet bij: wie de container overneemt, kan de log niet meer wissen.
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  # IP-adres en gebruikersnaam zijn persoonsgegevens (A-11): 30 dagen en dan echt weg, niet een dag later.
  retention_in_days                       = 30
  immediate_data_purge_on_30_days_enabled = true
  # Een rem op de kosten, geen filter: bij 0,1 GB op een dag stopt het verzamelen tot de volgende dag.
  daily_quota_gb = 0.1
  tags           = local.tags
}
