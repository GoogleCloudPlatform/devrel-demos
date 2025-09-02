# MDView Development Plan

## 1. Workflow

This project will be developed following a structured, task-based workflow. 

1.  **Follow the Plan:** We will execute the tasks sequentially as laid out in the "Task Breakdown" section below.
2.  **Update on Completion:** After completing each task, I will update this file (`plan.md`) by marking the task as complete and adding brief implementation notes in a dedicated section.
3.  **Design Synchronization:** If any part of the implementation requires a change to the agreed-upon design, I will first update `arch.md`, explain the change, and await your approval before proceeding.
4.  **Review and Approval:** I will pause for your review and approval after creating or modifying files and before executing commands, ensuring you are in full control of the process.

## 2. Task Breakdown

### ☑ Task 1: Project Scaffolding

*   **Objective:** Create the necessary files and directories as defined in `arch.md`.
*   **Actions:**
    *   Create the `mdview` executable file.
    *   Create the `viewer.py` module.
    *   Create the `setup.py` script.
    *   Create the `requirements.txt` file.

### ☑ Task 2: Implement the `Viewer` Class

*   **Objective:** Write the core rendering and pagination logic in `viewer.py`.
*   **Actions:**
    *   Define the `Viewer` class.
    *   Implement the `__init__` method to store the markdown content.
    *   Implement the `show` method using `rich.console.Console`, `rich.markdown.Markdown`, and the `console.pager()` context manager.

### ☑ Task 3: Implement the Executable Script

*   **Objective:** Write the main entry point logic in the `mdview` file.
*   **Actions:**
    *   Add the `#!/usr/bin/env python3` shebang.
    *   Implement argument parsing using `argparse` for the `file_path`.
    *   Add file validation and error handling (file not found, permissions).
    *   Read the file content.
    *   Instantiate the `Viewer` class and call its `show()` method.

### ☑ Task 4: Define Dependencies and Setup

*   **Objective:** Create the `requirements.txt` and `setup.py` files to make the project installable.
*   **Actions:**
    *   Add `rich` to `requirements.txt`.
    *   Implement the `setup.py` script, defining the package metadata and the `console_scripts` entry point to create the `mdview` command.

### ☐ Task 5: Testing and Verification

*   **Objective:** Ensure the tool works as expected.
*   **Actions:**
    *   Create a sample `test.md` with various markdown elements, including a long code block.
    *   Make the `mdview` script executable (`chmod +x mdview`).
    *   Test the script directly: `./mdview test.md`.
    *   Test the installation and entry point:
        *   `pip install .`
        *   `mdview test.md`
    *   Confirm that rendering, highlighting, and pagination all function correctly.

## 3. Implementation Notes

*(This section will be filled in as tasks are completed.)*

**Task 1: Project Scaffolding**
*   **Status:** Complete
*   **Notes:** Created empty files `mdview`, `viewer.py`, `setup.py`, and `requirements.txt` as the initial project structure.

**Task 2: Implement the `Viewer` Class**
*   **Status:** Complete
*   **Notes:** Implemented the `Viewer` class in `viewer.py`. It uses the `rich` library to create a `Markdown` object and displays it within a pager for easy navigation. The `monokai` theme is used for syntax highlighting.

**Task 3: Implement the Executable Script**
*   **Status:** Complete
*   **Notes:** Wrote the main executable script `mdview`. It uses `argparse` to handle command-line arguments and includes error handling for common file-related issues. It reads the specified file and passes the content to the `Viewer` class.

**Task 4: Define Dependencies and Setup**
*   **Status:** Complete
*   **Notes:** Added `rich` to `requirements.txt` and created the `setup.py` script. The setup script is configured to create the `mdview` console command upon installation. It was slightly improved from the original design to be more robust.
