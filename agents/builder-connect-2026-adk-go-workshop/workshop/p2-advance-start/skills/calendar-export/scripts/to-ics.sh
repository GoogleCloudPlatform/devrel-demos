#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Turns sessions, one per line as "YYYY-MM-DD HH:MM HH:MM Title" in Warsaw
# time, into an iCalendar (.ics) file.
#
#   to-ics.sh sessions.txt my-plan.ics
set -euo pipefail
in=${1:?usage: to-ics.sh <sessions.txt> <file.ics>}
out=${2:?usage: to-ics.sh <sessions.txt> <file.ics>}

# Warsaw time to UTC, which every calendar app reads the same way.
utc() { TZ=UTC date -d "TZ=\"Europe/Warsaw\" $1 $2" +%Y%m%dT%H%M%SZ; }
now=$(date -u +%Y%m%dT%H%M%SZ)

n=0
{
  printf 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ADK workshop//concierge//EN\r\n'
  # The || keeps a last line that has no newline at the end.
  while read -r day start end title || [[ -n ${day:-} ]]; do
    [[ -z ${day:-} || $day == \#* ]] && continue
    n=$((n + 1))
    # Commas and semicolons are separators in iCalendar text.
    title=${title//,/\\,}
    title=${title//;/\\;}
    printf 'BEGIN:VEVENT\r\nUID:%s-%d@adk-concierge\r\nDTSTAMP:%s\r\nDTSTART:%s\r\nDTEND:%s\r\nSUMMARY:%s\r\nLOCATION:PGE Narodowy\\, Warsaw\r\nEND:VEVENT\r\n' \
      "$now" "$n" "$now" "$(utc "$day" "$start")" "$(utc "$day" "$end")" "$title"
  done <"$in"
  printf 'END:VCALENDAR\r\n'
} >"$out"
echo "Wrote $n sessions to $out"
