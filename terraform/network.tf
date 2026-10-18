# Eén netwerk voor app en database: de database krijgt geen publiek adres (B-02, F-03).
resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.name}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.20.0.0/16"]
  tags                = local.tags
}

# Voor de Container Apps-omgeving: minimaal /27 en gedelegeerd aan Microsoft.App/environments.
resource "azurerm_subnet" "apps" {
  name                 = "snet-apps"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.20.0.0/27"]

  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Alleen voor PostgreSQL: minimaal /28, gedelegeerd, en er mag niets anders in.
resource "azurerm_subnet" "db" {
  name                 = "snet-db"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.20.1.0/28"]
  # Zet Azure zelf bij de eerste server, voor het archiveren van het transactielog (WAL) naar Storage. Hier vastgelegd,
  # anders haalt de volgende apply hem weg.
  service_endpoint {
    service = "Microsoft.Storage"
  }

  delegation {
    name = "postgres"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# De database is alleen met een privé-DNS-naam te vinden, en alleen vanuit dit netwerk.
resource "azurerm_private_dns_zone" "db" {
  name                = "${local.unique}.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "db" {
  name                 = "vnet-${local.name}"
  private_dns_zone_id  = azurerm_private_dns_zone.db.id
  virtual_network_id   = azurerm_virtual_network.main.id
  registration_enabled = false
  tags                 = local.tags
}
