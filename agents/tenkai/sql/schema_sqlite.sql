CREATE TABLE experiments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT,
			timestamp DATETIME,
			config_path TEXT,
			report_path TEXT,
			results_path TEXT,
			status TEXT,
			reps INTEGER,
			concurrent INTEGER,
			total_jobs INTEGER DEFAULT 0,
			error_message TEXT,
			pid INTEGER,
			description TEXT,
			duration INTEGER DEFAULT 0,
			config_content TEXT,
			report_content TEXT,
			execution_control TEXT,
			experiment_control TEXT,
			ai_analysis TEXT
		, is_locked BOOLEAN DEFAULT 0, annotations TEXT DEFAULT '');
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE run_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			experiment_id INTEGER,
			alternative TEXT,
			scenario TEXT,
			repetition INTEGER,
			duration INTEGER,
			error TEXT,
			tests_passed INTEGER,
			tests_failed INTEGER,
			lint_issues INTEGER,
			raw_json TEXT,
            total_tokens INTEGER DEFAULT 0,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			tool_calls_count INTEGER DEFAULT 0,
			failed_tool_calls INTEGER DEFAULT 0,
			loop_detected BOOLEAN DEFAULT 0,
			stdout TEXT,
			stderr TEXT,
			is_success BOOLEAN DEFAULT 0,
			validation_report TEXT,
			status TEXT,
			reason TEXT, cached_tokens INTEGER DEFAULT 0, model TEXT, session_id TEXT, model_duration INTEGER DEFAULT 0,
			FOREIGN KEY(experiment_id) REFERENCES experiments(id)
		);
CREATE TABLE run_events (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			type TEXT, -- "tool", "message"
			timestamp DATETIME,
			payload TEXT, -- JSON content
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);
CREATE VIEW messages AS 
			SELECT 
				id, 
				run_id, 
				json_extract(payload, '$.role') as role,
				json_extract(payload, '$.content') as content,
				timestamp
			FROM run_events 
			WHERE type = 'message'
/* messages(id,run_id,role,content,timestamp) */;
CREATE TABLE run_files (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			path TEXT,
			content TEXT,
			is_generated BOOLEAN,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);
CREATE TABLE test_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			name TEXT,
			status TEXT,
			duration_ns INTEGER,
			output TEXT,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);
CREATE TABLE lint_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			file TEXT,
			line INTEGER,
			col INTEGER,
			message TEXT,
			severity TEXT,
			rule_id TEXT,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);
CREATE UNIQUE INDEX idx_experiments_name_ts ON experiments(name, timestamp);
CREATE UNIQUE INDEX idx_run_results_unique_run ON run_results(experiment_id, alternative, scenario, repetition);
CREATE TABLE IF NOT EXISTS "config_blocks" (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				type TEXT NOT NULL,
				content TEXT NOT NULL,
				UNIQUE(name, type)
			);
CREATE TABLE test_table (id int);
CREATE VIEW tool_usage AS 
			SELECT 
				id, 
				run_id, 
				json_extract(payload, '$.name') as name,
				json_extract(payload, '$.args') as args,
				json_extract(payload, '$.status') as status,
				json_extract(payload, '$.output') as output,
				json_extract(payload, '$.error') as error,
				json_extract(payload, '$.duration') as duration,
				timestamp
			FROM run_events 
			WHERE type = 'tool'
/* tool_usage(id,run_id,name,args,status,output,error,duration,timestamp) */;
