-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

CREATE OR REPLACE PROCEDURE evaluate_vector_recall(
    table_name_param text,
    vector_dimensions integer,
    vector_col_param text DEFAULT 'd',
    id_col_param text DEFAULT 'id',
    k_param integer DEFAULT 5,
    sample_size_param integer DEFAULT 100
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Array to hold the vectors sampled for the recall evaluation
    sample_vectors vector[];
    -- Variable to hold the current vector being searched for
    current_vector vector;
    -- Arrays to hold the result IDs from exact and approximate searches
    exact_ids text[];
    approx_ids text[];
    -- Metrics variables
    overlap_count integer;
    vector_recall double precision;
    sum_recall double precision := 0.0;
    min_recall double precision := 1.0;
    max_recall double precision := 0.0;
    actual_dimensions integer;
    actual_sample_size integer;
    total_queries integer := 0;
BEGIN
    RAISE NOTICE 'Starting vector similarity search recall evaluation...';
    RAISE NOTICE 'Target table: %, Expected dimensions: %', table_name_param, vector_dimensions;
    RAISE NOTICE 'Parameters - Vector Column: %, ID Column: %, K: %, Sample Size: %',
                 vector_col_param, id_col_param, k_param, sample_size_param;

    -- Validate vector column exists and dimension matches
    BEGIN
        EXECUTE format('SELECT vector_dims(%I) FROM %I WHERE %I IS NOT NULL LIMIT 1',
                       vector_col_param, table_name_param, vector_col_param)
        INTO actual_dimensions;

        IF actual_dimensions IS NULL THEN
            RAISE EXCEPTION 'Could not find any non-NULL vectors in column % of table %. The table might be empty or contains only NULLs.',
                            vector_col_param, table_name_param;
        END IF;

        IF actual_dimensions != vector_dimensions THEN
            RAISE EXCEPTION 'Vector dimension mismatch. Expected dimension %, but found dimension % in table %.',
                            vector_dimensions, actual_dimensions, table_name_param;
        END IF;
    EXCEPTION
        WHEN undefined_table THEN
            RAISE EXCEPTION 'Table "%" does not exist.', table_name_param;
        WHEN undefined_column THEN
            RAISE EXCEPTION 'Column "%" does not exist in table "%".', vector_col_param, table_name_param;
    END;

    -- Validate ID column exists
    BEGIN
        EXECUTE format('SELECT %I FROM %I LIMIT 1', id_col_param, table_name_param);
    EXCEPTION
        WHEN undefined_column THEN
            RAISE EXCEPTION 'ID column "%" does not exist in table "%". Cannot measure recall.',
                            id_col_param, table_name_param;
    END;

    -- Select random sample vectors (ignoring nulls)
    RAISE NOTICE 'Selecting % random vectors for sampling from %...', sample_size_param, table_name_param;
    EXECUTE format('SELECT array_agg(%I) FROM (SELECT %I FROM %I WHERE %I IS NOT NULL ORDER BY random() LIMIT $1) AS random_sample',
                   vector_col_param, vector_col_param, table_name_param, vector_col_param)
    INTO sample_vectors
    USING sample_size_param;

    IF sample_vectors IS NULL OR COALESCE(array_length(sample_vectors, 1), 0) = 0 THEN
        RAISE EXCEPTION 'Could not retrieve any sample vectors. The table % might be empty or all vectors are NULL.', table_name_param;
    END IF;

    actual_sample_size := array_length(sample_vectors, 1);
    IF actual_sample_size < sample_size_param THEN
        RAISE WARNING 'Could not retrieve % sample vectors. Using % available sample vectors instead.',
                      sample_size_param, actual_sample_size;
    END IF;

    -- Iterate through sampled vectors to calculate recall
    FOREACH current_vector IN ARRAY sample_vectors
    LOOP
        -- 1. Find exact nearest neighbors (ground truth) by forcing sequential scan
        SET LOCAL enable_indexscan = off;
        SET LOCAL enable_bitmapscan = off;
        EXECUTE format('SELECT array_agg(%I::text) FROM (SELECT %I FROM %I ORDER BY %I <=> $1 LIMIT $2) AS exact_search',
                       id_col_param, id_col_param, table_name_param, vector_col_param)
        INTO exact_ids
        USING current_vector, k_param;

        -- 2. Find approximate nearest neighbors (allowing index scan)
        SET LOCAL enable_indexscan = on;
        SET LOCAL enable_bitmapscan = on;
        EXECUTE format('SELECT array_agg(%I::text) FROM (SELECT %I FROM %I ORDER BY %I <=> $1 LIMIT $2) AS approx_search',
                       id_col_param, id_col_param, table_name_param, vector_col_param)
        INTO approx_ids
        USING current_vector, k_param;

        -- 3. Calculate overlap
        IF exact_ids IS NOT NULL AND approx_ids IS NOT NULL THEN
            SELECT COUNT(*) INTO overlap_count
            FROM unnest(approx_ids) a
            JOIN unnest(exact_ids) e ON a = e;

            vector_recall := overlap_count::double precision / k_param;
            sum_recall := sum_recall + vector_recall;

            IF vector_recall < min_recall THEN min_recall := vector_recall; END IF;
            IF vector_recall > max_recall THEN max_recall := vector_recall; END IF;

            total_queries := total_queries + 1;
        END IF;
    END LOOP;

    -- Print recall report
    IF total_queries > 0 THEN
        RAISE NOTICE '------------------------------------------------------------------------';
        RAISE NOTICE 'Recall Evaluation Finished.';
        RAISE NOTICE 'Total queries evaluated: %', total_queries;
        RAISE NOTICE 'Average Recall@%:        %%%', k_param, round(((sum_recall / total_queries) * 100.0)::numeric, 2);
        RAISE NOTICE 'Minimum Recall@%:        %%%', k_param, round((min_recall * 100.0)::numeric, 2);
        RAISE NOTICE 'Maximum Recall@%:        %%%', k_param, round((max_recall * 100.0)::numeric, 2);
        RAISE NOTICE '------------------------------------------------------------------------';
    ELSE
        RAISE WARNING 'No recall queries were successfully evaluated.';
    END IF;
END;
$$;

