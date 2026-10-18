# West Europe neemt geen nieuwe tenants aan, en in Germany West Central mag deze subscription geen PostgreSQL maken.
# France Central is van wat wel mag het dichtst bij Nederland; database.tf controleert de regio al bij het plan.
variable "location" {
  type    = string
  default = "francecentral"
}

# De image van de app met een vaste tag of digest, nooit latest (MIT-03); de pipeline bouwt en pusht hem.
variable "app_image" {
  type = string
}

# Zelfde hoofdversie als lokaal in compose.yaml.
variable "postgres_version" {
  type    = string
  default = "18"
}

# 0: de app slaapt als niemand hem gebruikt (geen kosten, maar de eerste aanvraag is traag). Hacking week: 1.
variable "min_replicas" {
  type    = number
  default = 0
}

# Hackstand (MC-18): alleen tijdens de hacking week op hackweek.
variable "throttle_ip_mode" {
  type    = string
  default = "strict"

  validation {
    condition     = contains(["strict", "hackweek"], var.throttle_ip_mode)
    error_message = "Kies strict of hackweek."
  }
}

# Waar de alert bij een blokkade heen gaat (alerts.tf); deployment.py vult het adres van az login in. Niet in de repo: die is openbaar.
variable "alert_email" {
  type = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+[.][A-Za-z]{2,}$", var.alert_email))
    error_message = "Geef een e-mailadres, zoals naam@voorbeeld.nl."
  }
}

variable "throttle_pair_exempt_users" {
  type    = string
  default = ""
}

# Ophogen maakt nieuwe databasewachtwoorden en een nieuwe sessiesleutel; dat laatste logt iedereen uit.
# Start daarna de schema-job: die zet het nieuwe wachtwoord van notities_app in de database.
variable "secret_version" {
  type    = number
  default = 1
}
