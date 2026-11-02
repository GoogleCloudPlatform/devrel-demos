---
name: session-notes
description: Keeps the attendee's notes for conference sessions as Markdown files in the workspace, and summarizes them. Use when the attendee wants to take notes on a talk, add to their notes, or review what they noted.
---

# Session notes

Notes live in the workspace, one file per session, in `notes/`: for example
`notes/adk-a2a-workshop.md`. Use short, lowercase file names with hyphens.

## Start notes for a session

1. Look the session up with the agenda tools for its exact title, date, time,
   track and speakers.
2. Load `assets/template.md` with `load_skill_resource`, fill in the session
   details and anything the attendee already said, and save it with
   `write_file`.

## Add to notes

Read the file with `read_file`, add the new points under the right heading,
and save the whole file again with `write_file`. Keep the attendee's words.

## Questions for the speaker

When the attendee wants questions to ask, load `references/questions.md` and
suggest two or three that fit the session.

## Summarize

List the notes with the bash tool (`ls notes`), read each file with
`read_file`, and give a short summary per session, followed by everything the
attendee wanted to follow up on.
