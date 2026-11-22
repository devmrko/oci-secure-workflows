variable "target_subnet_id" { type = string }
variable "client_cidrs" {
  type = set(string)
  validation {
    condition     = length(var.client_cidrs) > 0 && alltrue([for c in var.client_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"])
    error_message = "Supply explicit IPv4 client CIDRs; 0.0.0.0/0 is not accepted for Bastion."
  }
}
variable "target_ports" {
  type    = set(number)
  default = [22]
  validation {
    condition     = length(var.target_ports) > 0 && alltrue([for p in var.target_ports : p >= 1 && p <= 65535 && floor(p) == p])
    error_message = "target_ports must contain TCP ports 1..65535."
  }
}
variable "ttl_seconds" {
  type    = number
  default = 10800
  validation {
    condition     = var.ttl_seconds >= 1800 && var.ttl_seconds <= 10800 && floor(var.ttl_seconds) == var.ttl_seconds
    error_message = "TTL must be 1800..10800 seconds."
  }
}
resource "oci_bastion_bastion" "access" {
  bastion_type                 = "STANDARD"
  compartment_id               = var.compartment_id
  target_subnet_id             = var.target_subnet_id
  name                         = var.name
  client_cidr_block_allow_list = sort(tolist(var.client_cidrs))
  max_session_ttl_in_seconds   = var.ttl_seconds
  dns_proxy_status             = "ENABLED"
}
resource "oci_core_network_security_group" "backend" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "${var.name}-backend"
}
resource "oci_core_network_security_group_security_rule" "bastion_to_backend" {
  for_each                  = toset([for p in var.target_ports : tostring(p)])
  network_security_group_id = oci_core_network_security_group.backend.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "${oci_bastion_bastion.access.private_endpoint_ip_address}/32"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      min = tonumber(each.value)
      max = tonumber(each.value)
    }
  }
}
output "bastion_id" { value = oci_bastion_bastion.access.id }
output "private_endpoint_ip" { value = oci_bastion_bastion.access.private_endpoint_ip_address }
output "backend_nsg_id" { value = oci_core_network_security_group.backend.id }
