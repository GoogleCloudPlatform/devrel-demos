-- Dynamically update sequence values for all identity columns in the public schema
DO $$
DECLARE
    rec RECORD;
    max_val bigint;
    seq_name text;
BEGIN
    FOR rec IN 
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns 
        WHERE is_identity = 'YES' 
          AND table_schema = 'public'
    LOOP
        -- Get the sequence name
        seq_name := pg_get_serial_sequence(format('%I.%I', rec.table_schema, rec.table_name), rec.column_name);
        
        IF seq_name IS NOT NULL THEN
            -- Get current max value
            EXECUTE format('SELECT MAX(%I) FROM %I.%I', rec.column_name, rec.table_schema, rec.table_name) INTO max_val;
            
            IF max_val IS NOT NULL THEN
                -- Set sequence to max_val so next value is max_val + 1
                PERFORM setval(seq_name, max_val);
                RAISE NOTICE 'Updated sequence % for %.% to %', seq_name, rec.table_name, rec.column_name, max_val;
            ELSE
                -- Table empty, reset to 1 (is_called=false means next value will be 1)
                PERFORM setval(seq_name, 1, false);
                RAISE NOTICE 'Reset sequence % for %.% to 1', seq_name, rec.table_name, rec.column_name;
            END IF;
        END IF;
    END LOOP;
END $$;