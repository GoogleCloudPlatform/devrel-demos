# Markdoc - Google Docs Extension

This Google Apps Script project converts Markdown syntax within a Google Doc into native Google Docs formatting.

## Features

- **Headings**: Converts `# Heading 1` through `###### Heading 6`
- **Lists**: Converts `- item` or `* item` to bulleted lists, and `1. item` to numbered lists.
- **Bold**: `**text**`
- **Italic**: `*text*`
- **Code**: `` `text` `` (Apply monospace font and gray background)
- **Links**: `[text](url)`

## Installation

### Option 1: Copy & Paste (Easiest)
1. Open a Google Doc.
2. Go to **Extensions** > **Apps Script**.
3. Clear the default code in `Code.gs`.
4. Copy the content of `Code.gs` from this repository and paste it there.
5. (Optional) Rename the project to "Markdoc".
6. Click the disk icon (Save) or press `Cmd/Ctrl + S`.
7. Reload your Google Doc.
8. You should see a new menu **Markdoc** in the toolbar.

### Option 2: Use CLASP (Command Line)
If you have `clasp` installed:
1. `clasp login`
2. `clasp create --type docs --title "Markdoc Extension"`
3. `clasp push`

## Usage

1. Write or paste Markdown content into your Google Doc.
2. Select **Markdoc** > **Render Markdown** from the menu.
3. The script will traverse the document and format the elements in place.

## Notes
- The script processes the entire document body.
- List conversion assumes the markdown list marker is at the start of the paragraph.
