CREATE OR REPLACE MATERIALIZED VIEW `$PROJECT_ID.$DATASET_ID.mv_ga4_ecommerce_items`
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 30
) AS
SELECT
  event_date, event_timestamp, event_name, user_pseudo_id, ecommerce.transaction_id,
  item.item_id,
  item.item_name,
  item.item_brand,
  item.item_variant,
  item.item_category,
  item.item_category2,
  item.item_category3,
  item.item_category4,
  item.item_category5,
  item.price_in_usd,
  item.price,
  item.quantity,
  item.item_revenue_in_usd,
  item.item_revenue,
  item.coupon,
  item.affiliation,
  item.item_list_name,
  item.promotion_name
FROM
  `$PROJECT_ID.$DATASET_ID.ga4_transactions`,
  UNNEST(items) AS item
WHERE
  ecommerce.transaction_id IS NOT NULL;
