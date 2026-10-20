# Deploying from GitHub (MIT-44): an identity of its own, which only a GitHub Actions job in the environment azure of this
# repo may use, through OIDC and without a password or key. It may only change the container app. Only with
# deploy_from_github: without it there is nothing a token could be exchanged for.
resource "azurerm_user_assigned_identity" "deploy" {
  count               = var.deploy_from_github ? 1 : 0
  name                = "id-${local.name}-deploy"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# Azure only accepts a token of a job in the environment azure; that environment only allows main and waits for an
# approval (deploy_azure.py sets it up). The subject must match exactly, with the IDs if GitHub puts them in.
resource "azurerm_federated_identity_credential" "github" {
  count                     = var.deploy_from_github ? 1 : 0
  name                      = "github-environment-azure"
  user_assigned_identity_id = azurerm_user_assigned_identity.deploy[0].id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "${var.github_oidc_prefix}:environment:azure"
}

# Only what replacing the image needs: reading and writing the container app and seeing its revisions. Not on the
# resource group: then it could also change the database, the job or the network.
resource "azurerm_role_definition" "deploy" {
  count       = var.deploy_from_github ? 1 : 0
  name        = "Deploy image of ${local.unique}"
  scope       = azurerm_resource_group.main.id
  description = "Replace the image of the container app of the notes app (MIT-44)."

  permissions {
    actions = [
      "Microsoft.App/containerApps/read",
      "Microsoft.App/containerApps/write",
      "Microsoft.App/containerApps/revisions/read",
    ]
  }

  assignable_scopes = [azurerm_resource_group.main.id]
}

resource "azurerm_role_assignment" "deploy" {
  count              = var.deploy_from_github ? 1 : 0
  scope              = azurerm_container_app.app.id
  role_definition_id = azurerm_role_definition.deploy[0].role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.deploy[0].principal_id
}

# A deployment from before deploy_from_github keeps these resources instead of making them again.
moved {
  from = azurerm_user_assigned_identity.deploy
  to   = azurerm_user_assigned_identity.deploy[0]
}

moved {
  from = azurerm_federated_identity_credential.github
  to   = azurerm_federated_identity_credential.github[0]
}

moved {
  from = azurerm_role_definition.deploy
  to   = azurerm_role_definition.deploy[0]
}

moved {
  from = azurerm_role_assignment.deploy
  to   = azurerm_role_assignment.deploy[0]
}
