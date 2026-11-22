variable "additional_routes" {
  description = "Preserve required SGW/DRG/peering routes explicitly; do not add another default route."
  type = list(object({
    destination       = string
    destination_type  = string
    network_entity_id = string
    description       = string
  }))
  default = []
  validation {
    condition     = alltrue([for r in var.additional_routes : r.destination != "0.0.0.0/0"])
    error_message = "NAT manages the only default route."
  }
}
resource "oci_core_nat_gateway" "outbound" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = var.name
  block_traffic  = false
}
# New table only. No existing route table or subnet is managed by this stack.
resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_id
  vcn_id         = var.vcn_id
  display_name   = "${var.name}-private"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.outbound.id
    description       = "Outbound internet through NAT"
  }
  dynamic "route_rules" {
    for_each = var.additional_routes
    content {
      destination       = route_rules.value.destination
      destination_type  = route_rules.value.destination_type
      network_entity_id = route_rules.value.network_entity_id
      description       = route_rules.value.description
    }
  }
}
output "nat_gateway_id" { value = oci_core_nat_gateway.outbound.id }
output "nat_public_ip" { value = oci_core_nat_gateway.outbound.nat_ip }
output "new_route_table_id" { value = oci_core_route_table.private.id }
