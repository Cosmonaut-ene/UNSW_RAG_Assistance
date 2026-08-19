# infra/terraform/versions.tf
# I3 in SPEC.md — Terraform scope is deliberately limited to VPS + DNS
# provisioning, not a full multi-node/multi-cloud setup.

terraform {
  required_version = ">= 1.5"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}
