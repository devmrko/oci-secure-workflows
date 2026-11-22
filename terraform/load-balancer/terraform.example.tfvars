profile        = "DEFAULT"
region         = "ap-seoul-1"
compartment_id = "ocid1.compartment.oc1..REPLACE"
vcn_id         = "ocid1.vcn.oc1.ap-seoul-1.REPLACE"
name           = "application-entry"
# Public regional subnet with Internet Gateway route.
subnet_ids     = ["ocid1.subnet.oc1.ap-seoul-1.REPLACE"]
client_cidrs   = ["203.0.113.10/32"]
certificate_id = "ocid1.certificate.oc1.ap-seoul-1.REPLACE"
backend_ips    = ["10.0.1.10"]
backend_port   = 8080
health_path    = "/health"
