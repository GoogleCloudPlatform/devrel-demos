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


SET @@dataset_project_id = '<<YOUR PROJECT ID>>';
SET @@dataset_id = 'hackathon_judge';


INSERT INTO `hackathons` (id, title, date, description, goal, status, criteria, bonus_criteria)
SELECT 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 'Productivity Hackathon', TIMESTAMP('2026-05-11T09:00:00Z'), 'A hackathon focused on building tools to enhance productivity and efficiency.', 'Build tools that drastically improve productivity and efficiency.', 'active', [STRUCT('crit_innov' as id, 'Innovation & Originality' as name, 'How unique and original is the productivity tool?\n\n**Low (1-2):** The project is essentially a \"Hello World\" of productivity (e.g., a basic CRUD to-do list with no unique features).\n**High (4-5):** The team identified a unique bottleneck—like \"context switching\" or \"decision fatigue\"—and built a tool specifically to kill that problem.' as description, 0.2 as weight, 5.0 as score, 5.0 as max_score), STRUCT('crit_theme' as id, 'Theme Alignment (Impact)' as name, 'Does the app actually save time or remove friction?\n\n**Low (1-2):** The app might be cool, but it doesn\'t actually make the user more efficient.\n**High (4-5):** Does the app actually save time? Does it remove friction? A 5/5 project makes the judges want to start using the app immediately for their own work.' as description, 0.3 as weight, 5.0 as score, 5.0 as max_score), STRUCT('crit_tech' as id, 'Technical Execution' as name, 'Quality of implementation and technical complexity.\n\n**Low (1-2):** Code is messy, or the "app" is just a series of static HTML pages with no logic.\n**High (4-5):** The team integrated complex elements (e.g., AI APIs, browser extensions, real-time sync, or advanced data visualization) successfully within the hackathon timeframe.' as description, 0.2 as weight, 5.0 as score, 5.0 as max_score), STRUCT('crit_ux' as id, 'User Experience (UX/UI)' as name, 'Design for focus, minimal distractions, and clear feedback.\n\n**Low (1-2):** Buttons don\'t work, text is unreadable, or the workflow is frustrating.\n**High (4-5):** For productivity tools, **less is more**. Points are awarded for "Flow State" design—minimal distractions, keyboard shortcuts, and clear feedback.' as description, 0.1 as weight, 5.0 as score, 5.0 as max_score), STRUCT('crit_pitch' as id, 'Pitch & Demo' as name, 'Quality of the presentation and live demonstration.\n\n**Low (1-2):** The team spent too much time on the technical stack and forgot to show the actual product.\n**High (4-5):** The team clearly demonstrated a "use case." They showed exactly how a user\'s life is better after using their tool.' as description, 0.2 as weight, 5.0 as score, 5.0 as max_score)], [STRUCT('crit_clean' as id, 'Clean Code' as name, 'Repository is well-documented with a clear README.' as description, 0.1 as weight, 2.0 as score, 2.0 as max_score), STRUCT('crit_access' as id, 'Accessibility' as name, 'Project considers screen readers, high contrast, or keyboard-only navigation.' as description, 0.05 as weight, 1.0 as score, 1.0 as max_score), STRUCT('crit_wow' as id, 'Wow Factor' as name, 'A specific feature that made the judges say "Wait, how did they build that in 24 hours?"' as description, 0.1 as weight, 2.0 as score, 2.0 as max_score)]
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `hackathons` WHERE id = 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '14710f6b-dbf7-4055-8106-9dbed109dae2', 'commitroom', 'CommitRoom', 'https://commitroom-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/commitroom', 'Team CommitRoom', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '14710f6b-dbf7-4055-8106-9dbed109dae2');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT 'f346dd70-809f-4ca5-93fa-28457a2ce0ef', 'daybreak-planner', 'Daybreak Planner', 'https://daybreak-planner-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/daybreak-planner', 'Team Daybreak', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = 'f346dd70-809f-4ca5-93fa-28457a2ce0ef');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT 'e7a76b65-305e-4801-bc4e-080236f1d3cf', 'decidr', 'Decidr', 'https://decidr-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/decidr', 'Team Decidr', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = 'e7a76b65-305e-4801-bc4e-080236f1d3cf');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '8fac700e-4398-4f77-a45e-b1ab21f512c3', 'eisenhower-matrix-tool', 'Eisenhower Matrix Tool', 'https://eisenhower-matrix-tool-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/eisenhower-matrix-tool', 'Team Eisenhower', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '8fac700e-4398-4f77-a45e-b1ab21f512c3');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '2ef0cf97-e221-4a8e-b107-2414456624a7', 'innerflow', 'InnerFlow', 'https://innerflow-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/innerflow', 'Team InnerFlow', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '2ef0cf97-e221-4a8e-b107-2414456624a7');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT 'd0f58408-8572-43ec-99b4-375eb2f6a23c', 'markdown-scratchpad', 'Markdown Scratchpad', 'https://markdown-scratchpad-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/markdown-scratchpad', 'Team Markdown', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = 'd0f58408-8572-43ec-99b4-375eb2f6a23c');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '442e7e86-102b-45f3-9406-6fda7b07c018', 'peakpulse', 'PeakPulse', 'https://peakpulse-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/peakpulse', 'Team PeakPulse', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '442e7e86-102b-45f3-9406-6fda7b07c018');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '7fa1a4a3-0e26-4c3a-9199-5445aa50321a', 'stakes-io', 'Stakes.io', 'https://stakes-io-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/stakes.io', 'Team Stakes', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '7fa1a4a3-0e26-4c3a-9199-5445aa50321a');

INSERT INTO `projects` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score)
SELECT '9f30bcc5-5a9e-4136-8aa4-7042574da33e', 'triotask', 'TrioTask', 'https://triotask-lmlks4hcoq-wl.a.run.app', NULL, 'https://github.com/moficodes/triotask', 'Team TrioTask', NULL, TIMESTAMP('2026-05-11'), 'CFB272DC-BDA6-45EF-B899-343B0EAB85E1', 0
FROM (SELECT 1) WHERE NOT EXISTS (SELECT 1 FROM `projects` WHERE id = '9f30bcc5-5a9e-4136-8aa4-7042574da33e');

