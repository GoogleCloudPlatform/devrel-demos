# MDView Technical Design

## 1. Objective

To create a command-line tool that renders Markdown files in the terminal with syntax highlighting and pagination. The tool will be read-only.

## 2. Core Technology

*   **Language:** Python 3
*   **Key Libraries:**
    *   **`rich`**: This is the primary dependency. It will be used for rendering Markdown, applying syntax highlighting to code blocks, and handling the pagination (viewing content in a scrollable pager).
    *   **`argparse`**: Part of the standard library, this will be used to parse the command-line arguments, specifically the path to the Markdown file.

## 3. Architecture & Design

The application will be split into two main files for separation of concerns: a main entrypoint script and a class dedicated to the viewing logic.

### 3.1. File Structure

```
md_viewer/
├── mdview              # Main executable script
├── viewer.py           # Contains the Viewer class
├── requirements.txt    # Lists dependencies (e.g., "rich")
├── setup.py            # Script for packaging and installation
├── user_guide.md       # User documentation
└── arch.md             # This document
```

### 3.2. Component Breakdown

#### `mdview` (Entry Point)

This script is the user-facing executable. Its responsibilities are:

1.  **Argument Parsing:** Use the `argparse` module to define and parse a single positional argument: `file_path`.
2.  **Input Validation:**
    *   Check if `file_path` is provided.
    *   Check if the file at `file_path` exists and is a file.
    *   Check if the application has permission to read the file.
3.  **File Reading:** Read the entire content of the specified Markdown file into a string.
4.  **Viewer Instantiation:** Create an instance of the `Viewer` class from `viewer.py`, passing the file content to its constructor.
5.  **Execution:** Call the main method of the `Viewer` instance to display the content.
6.  **Error Handling:** Catch exceptions (e.g., `FileNotFoundError`, `PermissionError`) and print user-friendly error messages to the console.

#### `viewer.py` (Viewer Class)

This module contains the core rendering logic, encapsulated in a `Viewer` class.

*   **`Viewer` Class:**
    *   **`__init__(self, content: str)`**: The constructor will accept the Markdown content as a string and store it as an instance attribute.
    *   **`show(self)`**: This is the primary method. It will perform the following steps:
        1.  Create a `rich.console.Console` object. This is the object used for all terminal output.
        2.  Create a `rich.markdown.Markdown` object from the stored content. This object is a renderable that `rich` knows how to draw. We can configure it with a `code_theme` for syntax highlighting (e.g., "monokai", "solarized-dark").
        3.  Use the `Console` object's pager as a context manager (`with console.pager():`). This is the key to the pagination feature. `rich` handles the screen clearing, content display, and keybindings for navigation (space, arrows, 'q' to quit) automatically.
        4.  Inside the context manager, call `console.print()` with the `Markdown` object.

### 4. Logic Flow

1.  The user executes the script from the command line: `mdview document.md`.
2.  The `mdview` script's `main` function is called.
3.  `argparse` processes the command line and gets the file path "document.md".
4.  The script opens and reads the file content.
5.  A `Viewer` object is instantiated: `viewer = Viewer(file_content)`.
6.  The `viewer.show()` method is invoked.
7.  `rich` takes over the terminal screen via `console.pager()`.
8.  The rendered, highlighted Markdown is displayed.
9.  The user can navigate up and down using arrow keys or page up/down. Pressing 'q' exits the pager.
10. The script finishes execution.

### 5. Installation & Distribution

The tool will be packaged using `setup.py` and `setuptools`. This will allow it to be installed via `pip`. The `setup.py` file will define a console script entry point, making `mdview` available as a command directly in the user's shell after installation.

**`requirements.txt`:**
```
rich
```

**`setup.py` (simplified):**
```python
from setuptools import setup, find_packages

setup(
    name="mdview",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "mdview=mdview:main",
        ],
    },
)
```
This approach provides a clean structure for building a robust and maintainable CLI tool.
