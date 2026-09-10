{{
    config(
        materialized = 'incremental',
        unique_key = 'review_id',
        on_schema_change = 'append_new_columns',
        description = 'Intermediate model enriching unstructured text using native BigQuery AI functions with capped retry threshold and 3D sentiment analysis.'
    )
}}

{# COST GOVERNANCE (PRE-HOOK SESSION TOKEN LIMIT CAP OPTION) #}
{# config(pre_hook = "SET @@ai.max_input_tokens = <YOUR_MAX_TOKEN_LIMIT>;") #}

/*
    Stage 2: Intermediate Layer (AI Enrichment & Architecture)
    ----------------------------------------------------------
    PIPELINE BEST PRACTICE RECOMMENDATIONS:
    
    1. COST GOVERNANCE
       - Pre-filtering: Excludes null/empty text before LLM invocation.
       - Token Cap Pre-hook: (See commented pre_hook option above).
       - Token Estimation: (See commented AI.COUNT_TOKENS in ai_raw below).
       
    2. MANDATORY INCREMENTALISM & POISON-PILL PROTECTION
       - Incremental Filter: Processes only new records (review_date > max_date).
       - Max Retries Threshold: Limits retries to 3 attempts max (ai_retry_count < 3).
       - Dead-Letter State: Permanently marks failed rows as 'MAX_RETRIES_EXCEEDED'.
       
    3. MANAGING LATENCY & PROMPT CACHING
       - Note: For demo readability, prompts are embedded inline. In enterprise production,
         extract prompts into dbt macros (e.g. macro get_sentiment_prompt) to enable
         reusable Prompt Caching across recurring pipeline runs.
         
    4. DRIFT & NON-DETERMINISM PROTECTION
       - Defensive SQL: Inspects LLM status and falls back gracefully.
       - dbt Test Suite: Enforces not_null assertions across generated outputs.
*/

with stg_reviews as (

    select
        review_id,
        customer_id,
        product_id,
        review_text,
        review_date
    from {{ ref('stg_customer_reviews') }}

    -- Pre-filtering: Exclude empty reviews to prevent unnecessary LLM token consumption
    where review_text is not null and trim(review_text) != ''

    {% if is_incremental() %}
    -- Incremental + Capped Retry Predicate: Process NEW rows OR RETRY failed rows (Max 3 attempts)
    and (
        review_date > (select max(review_date) from {{ this }})
        or review_id in (
            select review_id
            from {{ this }}
            where (sentiment_score is null or ai_generation_status != 'SUCCESS')
              and coalesce(ai_retry_count, 0) < 3  -- Capped at 3 retry attempts max
        )
    )
    {% endif %}

),

{% if is_incremental() %}
existing_retry_counts as (

    select
        review_id,
        coalesce(ai_retry_count, 0) as prev_retry_count
    from {{ this }}

),
{% endif %}

ai_raw as (

    select
        s.review_id,
        s.customer_id,
        s.product_id,
        s.review_text,
        s.review_date,

        {% if is_incremental() %}
        coalesce(e.prev_retry_count, 0) + 1 as ai_retry_count,
        {% else %}
        1 as ai_retry_count,
        {% endif %}

        -- COST GOVERNANCE OPTION: DRY-RUN TOKEN ESTIMATION BEFORE FULL INFERENCE
        -- AI.COUNT_TOKENS(s.review_text) as estimated_input_tokens,

        -- 1. Aspect 1: Product Quality Sentiment Score (1 to 5)
        AI.SCORE(
            (s.review_text, 'Score customer sentiment specifically regarding product quality, performance, and features on a scale from 1 (extremely negative) to 5 (extremely positive).')
        ) as raw_product_sentiment_score,

        -- 2. Aspect 2: Shipping & Delivery Sentiment Score (1 to 5)
        AI.SCORE(
            (s.review_text, 'Score customer sentiment specifically regarding shipping, delivery speed, and packaging on a scale from 1 (extremely negative) to 5 (extremely positive).')
        ) as raw_shipping_sentiment_score,

        -- 3. Aspect 3: Customer Service Sentiment Score (1 to 5)
        AI.SCORE(
            (s.review_text, 'Score customer sentiment specifically regarding customer service, support responsiveness, and return handling on a scale from 1 (extremely negative) to 5 (extremely positive).')
        ) as raw_customer_service_sentiment_score,

        -- 4. Overall Sentiment Score (1 to 5)
        AI.SCORE(
            (s.review_text, 'Score the overall sentiment of this customer review on a scale from 1 (extremely negative) to 5 (extremely positive).')
        ) as raw_overall_sentiment_score,

        -- 5. AI.GENERATE: Generate executive summary struct (result, status, full_response)
        AI.GENERATE(
            'Generate a concise, one-sentence executive summary of the following pet product review: ' || s.review_text
        ) as gen_struct

    from stg_reviews s

    {% if is_incremental() %}
    left join existing_retry_counts e on s.review_id = e.review_id
    {% endif %}

),

ai_enriched as (

    select
        review_id,
        customer_id,
        product_id,
        review_text,
        review_date,
        ai_retry_count,

        -- 3 Aspect-Specific Sentiment Dimensions
        raw_product_sentiment_score as product_sentiment_score,
        raw_shipping_sentiment_score as shipping_sentiment_score,
        raw_customer_service_sentiment_score as customer_service_sentiment_score,
        raw_overall_sentiment_score as sentiment_score,

        -- Inspect status field and fallback gracefully on safety blocks or errors
        case
            when gen_struct.status is null or gen_struct.status = '' then coalesce(gen_struct.result, 'Summary unavailable')
            else 'Summary blocked by safety policy'
        end as review_summary,

        -- Observability column: Track status and mark dead-letter rows after max retries
        case
            when gen_struct is not null and (gen_struct.status is null or gen_struct.status = '') then 'SUCCESS'
            when ai_retry_count >= 3 then 'MAX_RETRIES_EXCEEDED'
            else coalesce(gen_struct.status, 'FAILED_PENDING_RETRY')
        end as ai_generation_status

    from ai_raw

)

select * from ai_enriched
