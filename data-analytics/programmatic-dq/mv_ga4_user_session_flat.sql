CREATE OR REPLACE MATERIALIZED VIEW `$PROJECT_ID.$DATASET_ID.mv_ga4_user_session_flat`
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 30
) AS
SELECT
  event_date, event_timestamp, event_name, user_pseudo_id, user_id, stream_id, platform,
  device.category AS device_category,
  device.operating_system AS device_os,
  device.operating_system_version AS device_os_version,
  device.language AS device_language,
  device.web_info.browser AS device_browser,
  geo.continent AS geo_continent,
  geo.country AS geo_country,
  geo.region AS geo_region,
  geo.city AS geo_city,
  traffic_source.name AS traffic_source_name,
  traffic_source.medium AS traffic_source_medium,
  traffic_source.source AS traffic_source_source
FROM
  `$PROJECT_ID.$DATASET_ID.ga4_transactions`;
