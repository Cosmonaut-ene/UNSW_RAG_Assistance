# infra/terraform/main.tf
# Provisions exactly what I3 in SPEC.md scopes: one VPS + firewall +
# SSH key. k3s itself is installed separately (I1) -- this file's job
# ends at "a reachable Ubuntu box with SSH key auth and nothing else
# world-facing open yet".

resource "hcloud_ssh_key" "default" {
  name       = "${var.server_name}-key"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "hcloud_ssh_key" "ci_deploy" {
  count      = var.ci_deploy_public_key != "" ? 1 : 0
  name       = "${var.server_name}-ci-deploy-key"
  public_key = var.ci_deploy_public_key
}

resource "hcloud_firewall" "web" {
  name = "${var.server_name}-firewall"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_allowed_ips
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "chatbot" {
  name        = var.server_name
  server_type = var.server_type
  image       = var.server_image
  location    = var.location
  ssh_keys    = concat([hcloud_ssh_key.default.id], hcloud_ssh_key.ci_deploy[*].id)
  firewall_ids = [hcloud_firewall.web.id]

  user_data = file("${path.module}/cloud-init.yaml")

  labels = {
    project = "unsw-rag-chatbot"
    managed_by = "terraform"
  }
}
