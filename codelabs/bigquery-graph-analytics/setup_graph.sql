-- Lab 3: Property Graph Definitive Schema Object Compilation

CREATE OR REPLACE PROPERTY GRAPH `lost_cargo_dataset.logistics_network`
NODE TABLES (
  `lost_cargo_dataset.companies`
    LABEL Company
    PROPERTIES (company_id, company_name, headquarters_address, phone_number),
  `lost_cargo_dataset.manifests`
    LABEL Manifest
    PROPERTIES (shipment_id, seal_integrity_status, custodian_id),
  `lost_cargo_dataset.vessels`
    LABEL Vessel
    PROPERTIES (vessel_id, vessel_name),
  `lost_cargo_dataset.ports`
    LABEL Port
    PROPERTIES (port_id, port_name, latitude, longitude, country)
)
EDGE TABLES (
  `lost_cargo_dataset.manifests` AS manifests_edge
    SOURCE KEY (shipment_id) REFERENCES `lost_cargo_dataset.manifests` (shipment_id)
    DESTINATION KEY (vessel_id) REFERENCES `lost_cargo_dataset.vessels` (vessel_id)
    LABEL `EDGE_TABLE_PLACEHOLDER`
    NO PROPERTIES,
  `lost_cargo_dataset.vessels` AS vessels_edge
    SOURCE KEY (vessel_id) REFERENCES `lost_cargo_dataset.vessels` (vessel_id)
    DESTINATION KEY (company_id) REFERENCES `lost_cargo_dataset.companies` (company_id)
    LABEL `EDGE_TABLE_PLACEHOLDER`
    NO PROPERTIES,
  `lost_cargo_dataset.vessels` AS vessels_port_edge
    SOURCE KEY (vessel_id) REFERENCES `lost_cargo_dataset.vessels` (vessel_id)
    DESTINATION KEY (destination_port_id) REFERENCES `lost_cargo_dataset.ports` (port_id)
    LABEL BOUND_FOR
    NO PROPERTIES
);
