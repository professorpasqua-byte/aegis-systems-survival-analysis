-- Aegis Systems: raw -> clean, documented reference pipeline.
-- This is the documented reference pipeline. The repo's actual cleaning
-- step runs as pure Python inside data/generate_data.py, for portability
-- across environments without a compiled SQL engine installed.

CREATE OR REPLACE TABLE raw_panel AS
    SELECT * FROM read_csv('aegis_systems_raw.csv', header=true, all_varchar=true);

-- Step 1: deduplicate on employee_id plus month_index, since the raw
-- export occasionally repeats a person-month row.
CREATE OR REPLACE TABLE deduped AS
    SELECT * FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY employee_id, month_index
                   ORDER BY employee_id
               ) AS rn
        FROM raw_panel
    ) WHERE rn = 1;

-- Step 2: normalize inconsistent team casing and cast every column.
CREATE OR REPLACE TABLE clean_panel AS
SELECT
    employee_id,
    name,
    CASE
        WHEN lower(trim(team)) = 'platform infrastructure' THEN 'Platform Infrastructure'
        WHEN lower(trim(team)) = 'devops / sre' THEN 'DevOps / SRE'
        WHEN lower(trim(team)) = 'backend engineering' THEN 'Backend Engineering'
        WHEN lower(trim(team)) = 'data engineering' THEN 'Data Engineering'
        WHEN lower(trim(team)) = 'ml platform' THEN 'ML Platform'
        ELSE trim(team)
    END AS team,
    TRY_CAST(month_index AS INTEGER) AS month_index,
    TRY_CAST(tenure_months AS INTEGER) AS tenure_months,
    TRY_CAST(team_downsize_ratio AS DOUBLE) AS team_downsize_ratio,
    TRY_CAST(management_layer_shift AS BOOLEAN) AS management_layer_shift,
    TRY_CAST(ai_displacement_anxiety AS DOUBLE) AS ai_displacement_anxiety,
    TRY_CAST(psychological_safety_voice AS DOUBLE) AS psychological_safety_voice,
    TRY_CAST(slack_response_latency_delta AS DOUBLE) AS slack_response_latency_delta,
    TRY_CAST(off_hours_commits_delta AS DOUBLE) AS off_hours_commits_delta,
    status
FROM deduped;

COPY clean_panel TO 'aegis_systems_clean.csv' (HEADER, DELIMITER ',');
