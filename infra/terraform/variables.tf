# infra/terraform/variables.tf

variable "hcloud_token" {
  description = "Hetzner Cloud API token (Read & Write). Set via TF_VAR_hcloud_token env var or terraform.tfvars -- never commit this."
  type        = string
  sensitive   = true
}

variable "ssh_public_key_path" {
  description = "Path to the local SSH public key uploaded to Hetzner for server access."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "ci_deploy_public_key" {
  description = "Public half of the dedicated GitHub Actions deploy keypair (I2 in SPEC.md -- see .github/workflows/README.md for how it's generated and where the private half goes). Attached to every server this module creates so it doesn't need re-adding by hand after every infra/scripts/down.sh + up.sh cycle. Empty string skips it (e.g. before I2 exists yet)."
  type        = string
  default     = ""
}

variable "server_name" {
  description = "Name of the Hetzner Cloud server (also used as its hostname)."
  type        = string
  default     = "unsw-rag-chatbot"
}

variable "server_type" {
  description = "Hetzner server type. cx23 (2 vCPU / 4GB RAM / 40GB SSD) is the smallest size that comfortably runs k3s + this chatbot's containers (embeddings model, cross-encoder, ChromaDB) alongside the control plane. Confirmed against the Console's actual offering at apply time -- Hetzner's cx-series numbering has shifted (cx22 no longer exists, cx23 is its replacement)."
  type        = string
  default     = "cx23"
}

variable "server_image" {
  description = "Base OS image."
  type        = string
  default     = "ubuntu-22.04"
}

variable "location" {
  description = "Hetzner datacenter location. nbg1 (Nuremberg, Germany) is the default -- Hetzner has no Australia/US-Pacific region, so no location choice avoids the AU-to-demo latency; pick whichever is cheapest/available at apply time."
  type        = string
  default     = "nbg1"
}

variable "ssh_allowed_ips" {
  description = "CIDR blocks allowed to reach the server on port 22. Defaults to open (0.0.0.0/0) since the demo is meant to be reachable and there's no fixed office IP to restrict to -- SSH itself is still key-only (password auth disabled at the cloud-init level, see cloud-init.yaml), so this firewall rule isn't the only thing standing between the server and a brute-force attempt. Narrow this to your own IP/32 if you want tighter defense in depth."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
