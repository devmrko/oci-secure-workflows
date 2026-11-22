profile        = "DEFAULT"
region         = "ap-seoul-1"
compartment_id = "ocid1.compartment.oc1..REPLACE"
vcn_id         = "ocid1.vcn.oc1.ap-seoul-1.REPLACE"
name           = "private-outbound"
# Copy required Service Gateway / DRG / peering routes from the current table.
# This stack does not associate the new table with any subnet.
additional_routes = []
