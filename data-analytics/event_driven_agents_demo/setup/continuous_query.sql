EXPORT DATA
OPTIONS (
  format = "CLOUD_PUBSUB",
  uri = "https://pubsub.googleapis.com/projects/YOUR_PROJECT_ID/topics/cymbal-bank-escalations-topic"
)
AS (
  -- CTE: Extract the stream and calculate the base transaction-level heuristics
  WITH TransactionHeuristics AS (
    SELECT
      *,
      _CHANGE_TIMESTAMP AS bq_changed_ts,
    FROM APPENDS(TABLE `YOUR_PROJECT_ID.cymbal_bank.retail_transactions`, CURRENT_TIMESTAMP() - INTERVAL 10 MINUTE)
  )

  -- Final Step: Tumble, Aggregate, Format as JSON, and Filter
  SELECT
    TO_JSON_STRING(STRUCT(
      window_end,
      user_id,
      "Valued Customer" AS customer_name,
      COUNT(*) AS tx_count,
      SUM(amount) AS total_window_spend,
      MAX_BY(merchant_name, amount) AS highest_value_merchant,
      MAX_BY(merchant_category_code, amount) AS highest_value_mcc,
      LOGICAL_OR(is_international) AS contains_international_tx,
      LOGICAL_OR(NOT is_trusted_device) AS contains_untrusted_device_tx,
      100 AS final_risk_score,
      STRUCT(
        APPROX_COUNT_DISTINCT(location_country) > 1 AS is_impossible_travel,
        LOGICAL_OR(NOT is_trusted_device) AS has_security_mismatch,
        COUNT(*) > 4 AS is_high_velocity
      ) AS logic_signals
    )) AS data
  FROM TUMBLE(TABLE TransactionHeuristics, "bq_changed_ts", INTERVAL 1 MINUTE)
  GROUP BY
    window_start,
    window_end,
    user_id
  HAVING 
    APPROX_COUNT_DISTINCT(location_country) > 1
);
