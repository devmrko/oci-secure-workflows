mock_provider "oci" {}
variables {
  region         = "ap-seoul-1"
  compartment_id = "ocid1.compartment.oc1..example"
  vcn_id         = "ocid1.vcn.oc1.ap-seoul-1.example"
  name           = "offline-test"
}
run "outbound_only" {
  command = plan
  assert {
    condition     = length(oci_core_route_table.private.route_rules) == 1 && oci_core_nat_gateway.outbound.block_traffic == false
    error_message = "Expected one NAT default route."
  }
}
run "reject_second_default_route" {
  command = plan
  variables {
    additional_routes = [{ destination = "0.0.0.0/0", destination_type = "CIDR_BLOCK", network_entity_id = "example", description = "duplicate" }]
  }
  expect_failures = [var.additional_routes]
}
