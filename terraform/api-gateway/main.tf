variable "subnet_id" { type = string }
variable "client_cidrs" {
  type = set(string)
  validation {
    condition     = length(var.client_cidrs) > 0 && alltrue([for c in var.client_cidrs : can(cidrnetmask(c))])
    error_message = "Supply explicit IPv4 client CIDRs."
  }
}
variable "backend_ip" { type = string }
variable "backend_port" {
  type    = number
  default = 8080
}
variable "jwt_issuer" { type = string }
variable "jwt_audiences" {
  type = list(string)
  validation {
    condition     = length(var.jwt_audiences) > 0
    error_message = "At least one JWT audience is required."
  }
}
variable "jwks_uri" {
  type = string
  validation {
    condition     = startswith(var.jwks_uri, "https://")
    error_message = "JWKS URI must use HTTPS."
  }
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
resource "oci_core_network_security_group_security_rule" "backend_egress" {
  network_security_group_id = oci_core_network_security_group.frontend.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = "${var.backend_ip}/32"
  destination_type          = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = var.backend_port
      max = var.backend_port
    }
  }
}
# Allows retrieval of remote JWKS. Narrow using controlled JWKS infrastructure if available.
resource "oci_core_network_security_group_security_rule" "jwks_egress" {
  network_security_group_id = oci_core_network_security_group.frontend.id
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}
resource "oci_core_network_security_group_security_rule" "from_gateway" {
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
resource "oci_apigateway_gateway" "api" {
  compartment_id             = var.compartment_id
  display_name               = var.name
  endpoint_type              = "PUBLIC"
  subnet_id                  = var.subnet_id
  network_security_group_ids = [oci_core_network_security_group.frontend.id]
}
resource "oci_apigateway_deployment" "api" {
  compartment_id = var.compartment_id
  gateway_id     = oci_apigateway_gateway.api.id
  display_name   = var.name
  path_prefix    = "/api"
  specification {
    request_policies {
      authentication {
        type                        = "JWT_AUTHENTICATION"
        is_anonymous_access_allowed = false
        issuers                     = [var.jwt_issuer]
        audiences                   = var.jwt_audiences
        token_header                = "Authorization"
        token_auth_scheme           = "Bearer"
        public_keys {
          type                   = "REMOTE_JWKS"
          uri                    = var.jwks_uri
          is_ssl_verify_disabled = false
        }
      }
      rate_limiting {
        rate_in_requests_per_second = 10
        rate_key                    = "CLIENT_IP"
      }
    }
    routes {
      path    = "/health"
      methods = ["GET"]
      backend {
        type = "HTTP_BACKEND"
        url  = "http://${var.backend_ip}:${var.backend_port}/health"
      }
    }
  }
}
output "endpoint" { value = oci_apigateway_deployment.api.endpoint }
output "backend_nsg_id" { value = oci_core_network_security_group.backend.id }
