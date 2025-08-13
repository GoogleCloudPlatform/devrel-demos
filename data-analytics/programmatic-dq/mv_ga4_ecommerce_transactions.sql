CREATE OR REPLACE MATERIALIZED VIEW `$PROJECT_ID.$DATASET_ID.mv_ga4_ecommerce_transactions`
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 30
) AS
SELECT
  event_date, event_timestamp, user_pseudo_id, ecommerce.transaction_id,
  ecommerce.total_item_quantity,
  ecommerce.purchase_revenue_in_usd,
  ecommerce.purchase_revenue,
  ecommerce.refund_value_in_usd,
  ecommerce.refund_value,
  ecommerce.shipping_value_in_usd,
  ecommerce.shipping_value,
  ecommerce.tax_value_in_usd,
  ecommerce.tax_value,
  ecommerce.unique_items
FROM
  `$PROJECT_ID.$DATASET_ID.ga4_transactions`
WHERE
  ecommerce.transaction_id IS NOT NULL;
