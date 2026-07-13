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

CREATE OR REPLACE PROCEDURE benchmark_vector_search(
    n_repetitions integer,
    table_name_param text,
    vector_dimensions integer
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Array to hold the 100 vectors sampled for the benchmark run
    sample_vectors vector[];
    -- Variable to hold the current vector being searched for
    current_vector vector;
    -- Variables for timing
    overall_start_time timestamptz;
    overall_end_time timestamptz;
    repetition_start_time timestamptz;
    q_start timestamptz;
    q_end timestamptz;
    q_diff double precision; -- in milliseconds

    -- Metrics tracked across the entire benchmark
    global_min_latency double precision := 1e9;
    global_max_latency double precision := 0;
    global_sum_latency double precision := 0;
    overall_total_queries integer := 0;

    -- Variable for dimension validation
    actual_dimensions integer;
    actual_sample_size integer;

    -- Loop counter
    i int;
BEGIN
    RAISE NOTICE 'Starting vector similarity search benchmark...';
    RAISE NOTICE 'Target table: %, Repetitions: %, Expected dimensions: %', table_name_param, n_repetitions, vector_dimensions;

    -- Validate that the vector column "d" exists and dimensions match
    BEGIN
        EXECUTE format('SELECT vector_dims(d) FROM %I WHERE d IS NOT NULL LIMIT 1', table_name_param)
        INTO actual_dimensions;

        IF actual_dimensions IS NULL THEN
            RAISE EXCEPTION 'Could not find any non-NULL vectors in table %. The table might be empty or column "d" contains only NULLs.', table_name_param;
        END IF;

        IF actual_dimensions != vector_dimensions THEN
            RAISE EXCEPTION 'Vector dimension mismatch. Expected dimension %, but found dimension % in table %.', vector_dimensions, actual_dimensions, table_name_param;
        END IF;
    EXCEPTION
        WHEN undefined_table THEN
            RAISE EXCEPTION 'Table "%" does not exist.', table_name_param;
        WHEN undefined_column THEN
            RAISE EXCEPTION 'Table "%" does not have a column named "d".', table_name_param;
    END;

    RAISE NOTICE 'Dimension validation successful.';

    -- Fetch 100 random vectors to use as search queries
    RAISE NOTICE 'Selecting 100 random vectors for sampling from %...', table_name_param;
    EXECUTE format('SELECT array_agg(d) FROM (SELECT d FROM %I WHERE d IS NOT NULL ORDER BY random() LIMIT 100) AS random_sample', table_name_param)
    INTO sample_vectors;

    IF sample_vectors IS NULL OR COALESCE(array_length(sample_vectors, 1), 0) = 0 THEN
        RAISE EXCEPTION 'Could not retrieve any sample vectors. The table % might be empty or all vectors are NULL.', table_name_param;
    END IF;

    actual_sample_size := array_length(sample_vectors, 1);
    IF actual_sample_size < 100 THEN
        RAISE WARNING 'Could not retrieve 100 sample vectors. Using % available sample vectors instead.', actual_sample_size;
    END IF;

    RAISE NOTICE 'Starting main benchmark loop...';
    overall_start_time := clock_timestamp();

    -- The main outer loop that repeats the entire test (warmup + N repetitions)
    FOR i IN 0..n_repetitions LOOP
        repetition_start_time := clock_timestamp();

        -- Reset overall_start_time to start of repetition 1 to exclude warmup duration from QPS/Totals
        IF i = 1 THEN
            overall_start_time := clock_timestamp();
        END IF;

        DECLARE
            rep_min_latency double precision := 1e9;
            rep_max_latency double precision := 0;
            rep_sum_latency double precision := 0;
            rep_queries integer := 0;
            rep_duration double precision;
        BEGIN
            -- The inner loop that iterates through each of the sampled vectors
            FOREACH current_vector IN ARRAY sample_vectors
            LOOP
                q_start := clock_timestamp();
                -- Perform the core operation (limiting to top 5)
                EXECUTE format('SELECT 1 FROM %I ORDER BY d <=> $1 LIMIT 5', table_name_param)
                USING current_vector;
                q_end := clock_timestamp();

                q_diff := extract(epoch from (q_end - q_start)) * 1000.0; -- milliseconds

                -- Accumulate local statistics
                IF q_diff < rep_min_latency THEN rep_min_latency := q_diff; END IF;
                IF q_diff > rep_max_latency THEN rep_max_latency := q_diff; END IF;
                rep_sum_latency := rep_sum_latency + q_diff;
                rep_queries := rep_queries + 1;
            END LOOP;

            -- Calculate total time for this repetition
            rep_duration := extract(epoch from (clock_timestamp() - repetition_start_time));

            IF i = 0 THEN
                -- Warmup iteration: report it but do not add to global statistics
                RAISE NOTICE 'Warmup Repetition: Avg Latency = % ms (Min: % ms, Max: % ms) | QPS: %',
                             round((rep_sum_latency / rep_queries)::numeric, 3),
                             round(rep_min_latency::numeric, 3),
                             round(rep_max_latency::numeric, 3),
                             round((rep_queries / rep_duration)::numeric, 1);
            ELSE
                -- Accumulate global statistics
                IF rep_min_latency < global_min_latency THEN global_min_latency := rep_min_latency; END IF;
                IF rep_max_latency > global_max_latency THEN global_max_latency := rep_max_latency; END IF;
                global_sum_latency := global_sum_latency + rep_sum_latency;
                overall_total_queries := overall_total_queries + rep_queries;

                RAISE NOTICE 'Repetition %/%: Avg Latency = % ms (Min: % ms, Max: % ms) | QPS: %',
                             i, n_repetitions,
                             round((rep_sum_latency / rep_queries)::numeric, 3),
                             round(rep_min_latency::numeric, 3),
                             round(rep_max_latency::numeric, 3),
                             round((rep_queries / rep_duration)::numeric, 1);
            END IF;
        END;
    END LOOP;

    overall_end_time := clock_timestamp();

    -- Log overall summary metrics
    DECLARE
        total_benchmark_time double precision;
        overall_qps double precision;
    BEGIN
        total_benchmark_time := extract(epoch from (overall_end_time - overall_start_time));
        overall_qps := overall_total_queries / total_benchmark_time;

        RAISE NOTICE '------------------------------------------------------------------------';
        RAISE NOTICE 'Benchmark finished successfully.';
        RAISE NOTICE 'Total queries executed: % (excluding warmup)', overall_total_queries;
        RAISE NOTICE 'Total execution time:   % seconds (excluding warmup)', round(total_benchmark_time::numeric, 3);
        RAISE NOTICE 'Throughput (overall):   % QPS (excluding warmup)', round(overall_qps::numeric, 1);
        RAISE NOTICE '------------------------------------------------------------------------';
        RAISE NOTICE 'Latency Stats (excluding warmup):';
        RAISE NOTICE '  Average: % ms', round((global_sum_latency / overall_total_queries)::numeric, 3);
        RAISE NOTICE '  Minimum: % ms', round(global_min_latency::numeric, 3);
        RAISE NOTICE '  Maximum: % ms', round(global_max_latency::numeric, 3);
        RAISE NOTICE '------------------------------------------------------------------------';
    END;
END;
$$;

