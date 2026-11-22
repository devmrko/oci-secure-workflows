mock_provider "oci" {}
variables {
  region         = "ap-seoul-1"
  compartment_id = "ocid1.compartment.oc1..example"
  vcn_id         = "ocid1.vcn.oc1.ap-seoul-1.example"
  name           = "offline-test"
  subnet_ids     = ["ocid1.subnet.oc1.ap-seoul-1.example"]
  client_cidrs   = ["203.0.113.10/32"]
  certificate_id = "ocid1.certificate.oc1.ap-seoul-1.example"
  backend_ips    = ["10.0.1.10"]
}
run "https_and_private_backend_rules" {
  command = plan
  assert {
    condition     = oci_load_balancer_listener.https.port == 443 && tolist(oci_load_balancer_listener.https.ssl_configuration)[0].protocols == tolist(["TLSv1.2"])
    error_message = "Only HTTPS TLS 1.2 listener expected."
  }
  assert {
    condition     = oci_core_network_security_group_security_rule.from_lb.source_type == "NETWORK_SECURITY_GROUP"
    error_message = "Backend must be restricted to LB NSG."
  }
}
