mock_provider "oci" {}
variables {
  region         = "ap-seoul-1"
  compartment_id = "ocid1.compartment.oc1..example"
  vcn_id         = "ocid1.vcn.oc1.ap-seoul-1.example"
  name           = "offline-test"
  subnet_id      = "ocid1.subnet.oc1.ap-seoul-1.example"
  client_cidrs   = ["203.0.113.10/32"]
  backend_ip     = "10.0.1.10"
  jwt_issuer     = "https://identity.example.com/"
  jwt_audiences  = ["example"]
  jwks_uri       = "https://identity.example.com/jwks"
}
run "jwt_required" {
  command = plan
  assert {
    condition     = tolist(tolist(tolist(oci_apigateway_deployment.api.specification)[0].request_policies)[0].authentication)[0].is_anonymous_access_allowed == false
    error_message = "Anonymous access must remain disabled."
  }
}
run "reject_insecure_jwks" {
  command = plan
  variables { jwks_uri = "http://identity.example.com/jwks" }
  expect_failures = [var.jwks_uri]
}
