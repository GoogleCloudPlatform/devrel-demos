{{
    config(
        materialized = 'table',
        description = 'Mart model aggregating product reviews and generating semantic category rollups.'
    )
}}

/*
    Stage 3: Mart Layer (Semantic AI Aggregation & Business Intelligence)
    ---------------------------------------------------------------------
    Aggregates enriched reviews by product_id and AI-classified category.
    Combines traditional statistical metrics (counts, averages) with BigQuery's native
    AI.AGG function to synthesize high-level themes, complaints, and praise directly
    in SQL for executive reporting and BI dashboards.
*/

with enriched_reviews as (

    select * from {{ ref('int_reviews_enriched') }}

),

aggregated_insights as (

    select
        product_id,
        count(review_id) as total_reviews,
        round(avg(sentiment_score), 2) as avg_overall_sentiment_score,
        round(avg(product_sentiment_score), 2) as avg_product_sentiment_score,
        round(avg(shipping_sentiment_score), 2) as avg_shipping_sentiment_score,
        round(avg(customer_service_sentiment_score), 2) as avg_customer_service_sentiment_score,

        -- AI.AGG: Synthesize actionable product improvement recommendations & feature requests with defensive fallback
        coalesce(
            AI.AGG(
                review_text,
                'Synthesize customer feedback into a concise product manager briefing. Extract explicit feature requests, usability complaints, and concrete product improvement recommendations across these reviews, highlighting top priority fixes and enhancements. If no specific improvements are mentioned, state "No product improvement recommendations identified."'
            ),
            'No product improvement recommendations generated (insufficient data or safety policy block).'
        ) as product_improvement_recommendations

    from enriched_reviews
    group by
        product_id

)

select
    product_id,
    total_reviews,
    avg_overall_sentiment_score,
    avg_product_sentiment_score,
    avg_shipping_sentiment_score,
    avg_customer_service_sentiment_score,
    product_improvement_recommendations,
    current_timestamp() as aggregated_at

from aggregated_insights
