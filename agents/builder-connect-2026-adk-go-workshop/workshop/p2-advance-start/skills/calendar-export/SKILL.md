---
name: calendar-export
description: Turns conference sessions into an .ics calendar file that Google Calendar, Outlook and Apple Calendar can import. Use when the attendee wants their plan or some sessions in their own calendar.
---

# Export sessions to a calendar file

1. Get the sessions to export, each with its date, start and end time (Warsaw time) and exact title:
   - from a plan in the workspace, such as `my-plan.md`, with `read_file`, or
   - from the agenda tools, for sessions the attendee names.
2. Write them to `sessions.txt` in the workspace with `write_file`, one session per line:

   ```
   YYYY-MM-DD HH:MM HH:MM Title
   ```

   For example: `2026-11-03 12:05 13:30 ADK + A2A workshop`
3. Turn that file into a calendar file with the bash tool, which runs in the folder the agent runs in:

   ```
   bash skills/calendar-export/scripts/to-ics.sh sessions.txt my-plan.ics
   ```

4. Tell the attendee the file name and how many sessions it has, and how to import it. `references/import.md` explains importing.
