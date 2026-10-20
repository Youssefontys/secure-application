# West Europe takes no new tenants, in Germany West Central this subscription may not create PostgreSQL, and
# Belgium Central has no log search alert. France Central is the cheapest and is in the EU (Week 8);
# database.tf already checks the region at the plan.
variable "location" {
  type    = string
  default = "francecentral"
}

# The image of the app with a fixed tag or digest, never latest (MIT-03); the pipeline builds and pushes it.
variable "app_image" {
  type = string
}

# Same major version as locally in compose.yaml.
variable "postgres_version" {
  type    = string
  default = "18"
}

# 0: the app sleeps when nobody uses it (no cost, but the first request is slow). Hacking week: 1.
variable "min_replicas" {
  type    = number
  default = 0
}

# Hackmode (MC-18): only on hackweek during the hacking week.
variable "throttle_ip_mode" {
  type    = string
  default = "strict"

  validation {
    condition     = contains(["strict", "hackweek"], var.throttle_ip_mode)
    error_message = "Choose strict or hackweek."
  }
}

# Where the alert on a lockout goes (alerts.tf); deployment.py fills in the address of az login. Not in the repo: it is public.
variable "alert_email" {
  type = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+[.][A-Za-z]{2,}$", var.alert_email))
    error_message = "Give an email address, such as name@example.com."
  }
}

variable "throttle_pair_exempt_users" {
  type    = string
  default = ""
}

# Raising it makes new database passwords and a new session key; the latter logs everyone out.
# Then start the schema job: it puts the new password of notes_app in the database.
variable "secret_version" {
  type    = number
  default = 1
}
