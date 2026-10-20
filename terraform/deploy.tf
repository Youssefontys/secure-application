# Deploying from GitHub (MIT-44): an identity of its own, which only a GitHub Actions job in the environment azure of this
# repo may use, through OIDC and without a password or key. It may only change the container app.
resource "azurerm_user_assigned_identity" "deploy" {
  name                = "id-${local.name}-deploy"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# Azure only accepts a token of a job in the environment azure; that environment only allows main and waits for an
# approval (deploy_azure.py sets it up). The subject is case-sensitive, so the exact name of the repo.
resource "azurerm_federated_identity_credential" "github" {
  name                      = "github-environment-azure"
  user_assigned_identity_id = azurerm_user_assigned_identity.deploy.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:${var.github_repo}:environment:azure"
}

# Only what replacing the image needs: reading and writing the container app and seeing its revisions. Not on the
# resource group: then it could also change the database, the job or the network.
resource "azurerm_role_definition" "deploy" {
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
  scope              = azurerm_container_app.app.id
  role_definition_id = azurerm_role_definition.deploy.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.deploy.principal_id
}
