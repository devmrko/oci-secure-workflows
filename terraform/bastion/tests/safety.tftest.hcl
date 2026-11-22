mock_provider "oci" {}
variables {
  region           = "ap-seoul-1"
  compartment_id   = "ocid1.compartment.oc1..example"
  vcn_id           = "ocid1.vcn.oc1.ap-seoul-1.example"
  name             = "offline-test"
  target_subnet_id = "ocid1.subnet.oc1.ap-seoul-1.example"
  client_cidrs     = ["203.0.113.10/32"]
}
run "restricted_bastion" {
  command = plan
  assert {
    condition     = oci_bastion_bastion.access.dns_proxy_status == "ENABLED" && oci_bastion_bastion.access.max_session_ttl_in_seconds <= 10800
    error_message = "Bastion must support SOCKS5 with bounded TTL."
  }
}
run "reject_open_allowlist" {
  command = plan
  variables { client_cidrs = ["0.0.0.0/0"] }
  expect_failures = [var.client_cidrs]
}
run "reject_excess_ttl" {
  command = plan
  variables { ttl_seconds = 10801 }
  expect_failures = [var.ttl_seconds]
}
