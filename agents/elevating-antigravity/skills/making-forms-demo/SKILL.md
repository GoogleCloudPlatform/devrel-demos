---
name: making-forms-demo
description: >
  Interviews the user for critical implementation details needed to
  generate a Web Form. Manages FORM namespace in `user_prefs.json`.
  Use when making Web Forms.
---

# Making forms
Interviews the user for critical implementation details needed to generate a Web Form.

## Workflow Steps

1. **Confirm Intent & Hydrate State:**
   Check if `user_prefs.json` exists in the workspace root. If present, read the `"FORMS"` object to identify any previously saved preferences. Tell the user that a form has been identified and that a few questions must be answered (or confirmed) before building the form.

2. **Query Validation Type:**
   Invoke the `ask_question` tool to present the user with an option selection UI. If previously saved values exist in 
   `user_prefs.json`, prefix those option strings with `"(Current Setting) "` and list them first:
   * **Question:** "How would you like to handle field validation? (select all that apply)"
   * **Options:** ["Client-side validation", "Server-side validation"]

   Use the selected value as `FIELD_VALIDATION_TYPE`.

3. **Query Validation Location:**
   Invoke the `ask_question` tool to present the user with an option selection UI. If a previously saved value exists in 
   `user_prefs.json`, prefix that option string with `"(Current Setting) "` and list it first:
   * **Question:** "How would you like to handle validation messages?"
   * **Options:** ["Above the field", "Below the field", "Summary Card", "Tooltip"]

   Use the selected value as `FIELD_VALIDATION_LOCATION`.

4. **Persist User Preferences:**
   Write the user's selected form preferences to a `user_prefs.json` file in the workspace root directory using the `write_to_file` tool (or overwrite existing preferences). This guarantees that future agent invocations and subagents are grounded in the user's exact specifications without needing to re-interview them:

   ```json
   {
     "FORMS": {
       "FIELD_VALIDATION_TYPE": ["<SELECTED_VALUES>"],
       "FIELD_VALIDATION_LOCATION": "<SELECTED_VALUE>"
     }
   }
   ```

## Mock Skill Instructions
Since this skill is just a mock skill for illustrating how to create interviewer UI within the chat window, don't actually create a form. Instead:
1. Write the selections to `user_prefs.json` in the workspace root.
2. Output the form selections to the user as confirmation using the template below:

For each field:
**<FIELD_NAME>:** <SELECTED_VALUE>