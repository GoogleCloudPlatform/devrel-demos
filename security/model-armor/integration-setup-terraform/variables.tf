variable "project_id" {
  type        = string
  description = "Google Cloud project ID where integration is configured"
}

variable "vertex_ai_integration" {
  type        = bool
  description = "Flag whether to activate integration with Vertex AI"
  default     = true
}

variable "mcp_integration" {
  type        = bool
  description = "Flag whether to activate integration with Google Cloud MCP servers"
  default     = true
}