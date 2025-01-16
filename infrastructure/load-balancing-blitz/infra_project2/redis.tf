
# https://cloud.google.com/memorystore/docs/redis/connect-redis-instance-gce

resource "google_redis_instance" "cache" {
  name           = "memory-cache"
  memory_size_gb = 1
  replica_count  = 0

  maintenance_policy {

    weekly_maintenance_window {
      day = "SUNDAY"

      start_time {
        hours   = 3
        minutes = 0
        nanos   = 0
        seconds = 0
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
