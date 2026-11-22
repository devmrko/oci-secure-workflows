variable "subnet_ids" { type = list(string) }
variable "client_cidrs" {
  type = set(string)
  validation {
    condition     = length(var.client_cidrs) > 0 && alltrue([for c in var.client_cidrs : can(cidrnetmask(c))])
    error_message = "Supply explicit IPv4 client CIDRs."
  }
}
variable "certificate_id" { type = string }
variable "backend_ips" { type = set(string) }
variable "backend_port" {
  type    = number
  default = 8080
}
variable "health_path" {
  type    = string
  default = "/health"
}
variable "idle_timeout_seconds" {
  type    = number
  default = 300
}
resource "oci_core_network_security_group" "frontend" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "${var.name}-frontend"
}
resource "oci_core_network_security_group" "backend" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "${var.name}-backend"
}
resource "oci_core_network_security_group_security_rule" "https" {
  for_each                  = var.client_cidrs
  network_security_group_id = oci_core_network_security_group.frontend.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}
resource "oci_core_network_security_group_security_rule" "to_backend" {
  network_security_group_id = oci_core_network_security_group.frontend.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = oci_core_network_security_group.backend.id
  destination_type          = "NETWORK_SECURITY_GROUP"
  tcp_options {
    destination_port_range {
      min = var.backend_port
      max = var.backend_port
    }
  }
}
resource "oci_core_network_security_group_security_rule" "from_lb" {
  network_security_group_id = oci_core_network_security_group.backend.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = oci_core_network_security_group.frontend.id
  source_type               = "NETWORK_SECURITY_GROUP"
  tcp_options {
    destination_port_range {
      min = var.backend_port
      max = var.backend_port
    }
  }
}
resource "oci_load_balancer_load_balancer" "web" {
  compartment_id             = var.compartment_id
  display_name               = var.name
  shape                      = "flexible"
  is_private                 = false
  subnet_ids                 = var.subnet_ids
  network_security_group_ids = [oci_core_network_security_group.frontend.id]
  shape_details {
    minimum_bandwidth_in_mbps = 10
    maximum_bandwidth_in_mbps = 10
  }
}
resource "oci_load_balancer_backend_set" "app" {
  load_balancer_id = oci_load_balancer_load_balancer.web.id
  name             = "application"
  policy           = "ROUND_ROBIN"
  health_checker {
    protocol    = "HTTP"
    port        = var.backend_port
    url_path    = var.health_path
    return_code = 200
  }
}
resource "oci_load_balancer_backend" "app" {
  for_each         = var.backend_ips
  load_balancer_id = oci_load_balancer_load_balancer.web.id
  backendset_name  = oci_load_balancer_backend_set.app.name
  ip_address       = each.value
  port             = var.backend_port
}
# Explicit ECDHE+AES-GCM suite. Internal Assurance acceptance still needs review.
resource "oci_load_balancer_ssl_cipher_suite" "tls" {
  load_balancer_id = oci_load_balancer_load_balancer.web.id
  name             = "access-ecdhe-gcm"
  ciphers          = ["ECDHE-RSA-AES128-GCM-SHA256", "ECDHE-RSA-AES256-GCM-SHA384", "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-ECDSA-AES256-GCM-SHA384"]
}
resource "oci_load_balancer_listener" "https" {
  load_balancer_id         = oci_load_balancer_load_balancer.web.id
  default_backend_set_name = oci_load_balancer_backend_set.app.name
  name                     = "https"
  port                     = 443
  protocol                 = "HTTP"
  ssl_configuration {
    certificate_ids   = [var.certificate_id]
    protocols         = ["TLSv1.2"]
    cipher_suite_name = oci_load_balancer_ssl_cipher_suite.tls.name
  }
  connection_configuration {
    idle_timeout_in_seconds = var.idle_timeout_seconds
  }
}
output "load_balancer_ips" { value = oci_load_balancer_load_balancer.web.ip_address_details }
output "backend_nsg_id" { value = oci_core_network_security_group.backend.id }
