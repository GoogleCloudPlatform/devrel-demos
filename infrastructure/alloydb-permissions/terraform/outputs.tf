output "cloud_run_url" {
  value       = google_cloud_run_service.auth_issue_demo.status[0].url
  description = "The URL of the Cloud Run service."
}

output "alloydb_public_ip" {
  value       = google_alloydb_instance.rma_instance_1.public_ip_address
  description = "The public IP address of the AlloyDB instance."
}
