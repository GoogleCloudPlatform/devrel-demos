{{
    config(
        materialized = 'view',
        description = 'Staging model standardizing raw customer review schema and data types.'
    )
}}

/*
    Stage 1: Staging Layer
    ----------------------
    Standardizes column names, casts types, and formats timestamps from raw source data.
    Maps raw table columns (order_item_id -> review_id, order_id -> customer_id, review -> review_text).
    Lightweight view materialization ensures zero storage duplication before downstream enrichment.
*/

with source_reviews as (

    select * from {{ source('cymbal_pets', 'reviews') }}

),

source_orders as (

    select * from {{ source('cymbal_pets', 'orders') }}

),

renamed as (

    select
        cast(r.order_item_id as string) as review_id,
        cast(coalesce(o.customer_id, r.order_id) as string) as customer_id,
        cast(r.product_id as string) as product_id,
        cast(r.review as string) as review_text,
        cast(o.order_date as timestamp) as review_date

    from source_reviews r
    left join source_orders o on r.order_id = o.order_id
    where r.review is not null and trim(r.review) != ''

)

select * from renamed
