# infra/terraform/outputs.tf

output "server_ipv4" {
  description = "Public IPv4 address of the chatbot VPS. Use this to SSH in and to point a domain's A record at, once one exists."
  value       = hcloud_server.chatbot.ipv4_address
}

output "server_ipv6" {
  value = hcloud_server.chatbot.ipv6_address
}

output "server_id" {
  value = hcloud_server.chatbot.id
}
