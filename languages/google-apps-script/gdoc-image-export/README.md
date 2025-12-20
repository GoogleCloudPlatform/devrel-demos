# Google Docs Image Export

A Google Apps Script project that extracts all inline images from the current Google Doc and saves them to a specific folder in Google Drive.

## Features

- **Automated Extraction**: Scans the entire document for inline images.
- **Drive Integration**: Creates a new folder (named after the document) in Google Drive and saves all images there.
- **Custom Menu**: Adds an "Image Tools" menu to the Google Docs UI for easy access.

## Installation

1. Open a Google Doc.
2. Go to **Extensions** > **Apps Script**.
3. Copy the content of `Code.gs` into the script editor.
4. Save the project.
5. Reload the Google Doc.

## Usage

1. Open the Google Doc containing images.
2. Click **Image Tools** > **Extract & Save Images** in the menu bar.
3. Grant the necessary permissions when prompted.
4. The script will run and notify you when completion, providing a link to the Drive folder.
