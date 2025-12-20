-- demo
select package, test, action from all_tests;
select * from passed_tests;
select * from failed_tests;
select function_name, file, start_line, end_line from missing_coverage;
select test_name, function_name, start_line, end_line count from test_coverage where count > 0;
select file, line_number, content from all_code limit 10;

select file, line_number, content from all_code where (file, line_number) in (select file, start_line from test_coverage where count = 0);

select distinct ac.file, line_number, content, ifnull(count, 0) covered from all_code ac left join all_coverage cov on ac.file = cov.file and ac.line_number between cov.start_line and cov.end_line where ac.file not like '%_test.go';