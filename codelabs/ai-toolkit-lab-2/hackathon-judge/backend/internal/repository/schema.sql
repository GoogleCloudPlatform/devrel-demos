-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.



-- Set the default project and dataset for subsequent queries in this session.
SET @@dataset_project_id = '<<YOUR PROJECT ID>>';
SET @@dataset_id = 'hackathon_judge';

CREATE SCHEMA IF NOT EXISTS `hackathon_judge`;

-- Create a Connection Resource
/*
CREATE CONNECTION IF NOT EXISTS `<<REGION>>.connection-resource`
OPTIONS (
  connection_type = 'CLOUD_RESOURCE'
);
*/

-- Hackathons Table
CREATE TABLE IF NOT EXISTS `hackathons` (
    id STRING,
    title STRING,
    date TIMESTAMP,
    description STRING,
    goal STRING,
    status STRING,
    criteria ARRAY<STRUCT<id STRING, name STRING, description STRING, weight FLOAT64, score FLOAT64, max_score FLOAT64>>,
    bonus_criteria ARRAY<STRUCT<id STRING, name STRING, description STRING, weight FLOAT64, score FLOAT64, max_score FLOAT64>>
);

-- Projects Table
CREATE TABLE IF NOT EXISTS `projects` (
    id STRING,
    name STRING,
    title STRING,
    url STRING,
    readme_ref STRUCT< uri STRING, version STRING, authorizer STRING, details JSON>,
    github_url STRING,
    team_name STRING,
    document STRING,
    processing_date TIMESTAMP,
    hackathon_id STRING,
    score FLOAT64
);


-- Evaluations Table
CREATE TABLE IF NOT EXISTS `evaluations` (
    id STRING,
    project_id STRING,
    judge_id STRING,
    status STRING,
    criteria_json ARRAY<STRUCT<name STRING, description STRING, weight FLOAT64, score FLOAT64, max_score FLOAT64>>,
    total_score FLOAT64,
    comment STRING,
    created_at TIMESTAMP
);


-- -- Insert sample evaluation criteria with weights
-- INSERT INTO `criteria` (name, prompt, weight)
-- VALUES
--   ('Documentation', 'How clear, concise and thorough is the documentation?', 0.2),
--   ('Innovation', 'How creative and original is the project?', 0.3),
--   ('Design', 'How well-designed is the user interface and experience?', 0.2),
--   ('Impact', 'What is the potential impact of the project?', 0.3);


-- Create an External Table
/*
CREATE EXTERNAL TABLE IF NOT EXISTS `submissions_objects`
WITH CONNECTION `<<REGION>>.connection-resource`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://<<YOUR PROJECT ID>>-stabby/*']
);
*/
