# AlloyDB Support Database Schema Reference (`support_db`)

Use this schema reference when constructing SQL queries for the **AlloyDB Remote MCP**
tools (`execute_sql_read_only` and `execute_sql`).

## Connection Context
- **Project ID**: `devfest-project` (or `ALLOYDB_PROJECT_ID` configured in your environment)
- **Location / Region**: `us-west1` (or `ALLOYDB_REGION`)
- **Cluster**: `devfest-cluster` (or `ALLOYDB_CLUSTER`)
- **Instance**: `devfest-cluster-pr` (or `ALLOYDB_INSTANCE`)
- **Database**: `support_db`

## Tables

### `customers`
- `customer_id` (`VARCHAR(32)`, PK) — e.g. `'CUST-101'`
- `full_name` (`VARCHAR(120)`)
- `email` (`VARCHAR(160)`)
- `tier` (`VARCHAR(20)`) — `'STANDARD'`, `'PRO'`, `'ENTERPRISE'`
- `city` (`VARCHAR(80)`)

### `orders`
- `order_id` (`VARCHAR(32)`, PK) — e.g. `'ORD-9001'`
- `customer_id` (`VARCHAR(32)`, FK -> `customers.customer_id`)
- `product_name` (`VARCHAR(160)`)
- `amount_cad` (`NUMERIC(10,2)`)
- `order_status` (`VARCHAR(24)`) — `'PROCESSING'`, `'SHIPPED'`, `'DELIVERED'`, `'DELAYED'`, `'REFUNDED'`
- `ordered_at` (`TIMESTAMPTZ`)

### `support_tickets`
- `ticket_id` (`SERIAL`, PK)
- `customer_id` (`VARCHAR(32)`, FK -> `customers.customer_id`)
- `order_id` (`VARCHAR(32)`, nullable FK -> `orders.order_id`)
- `priority` (`VARCHAR(16)`) — `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'`
- `status` (`VARCHAR(20)`) — `'OPEN'`, `'IN_PROGRESS'`, `'ESCALATED'`, `'RESOLVED'`
- `issue_summary` (`TEXT`)
- `resolution_note` (`TEXT`, nullable)
- `embedding` (`vector(768)`, nullable — indexed with AlloyDB `scann`)
- `created_at` (`TIMESTAMPTZ`)
- `updated_at` (`TIMESTAMPTZ`)

## Safe Query Guidelines
- Prefer `execute_sql_read_only` for all `SELECT` triage queries.
- Use `execute_sql` **only** when updating `support_tickets.status` and `resolution_note` upon explicit user request.
- Always `LIMIT` diagnostic queries to 20 rows or fewer.
