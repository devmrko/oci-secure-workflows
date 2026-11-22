terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "= 9.14.0"
    }
  }
}
provider "oci" {
  region              = var.region
  config_file_profile = var.profile
}
variable "region" { type = string }
variable "profile" {
  type    = string
  default = "DEFAULT"
}
variable "compartment_id" { type = string }
variable "vcn_id" { type = string }
variable "name" { type = string }
