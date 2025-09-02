from rich.console import Console
from rich.markdown import Markdown

class Viewer:
    """A class to view Markdown content in the terminal."""

    def __init__(self, content: str):
        """
        Initializes the Viewer with the Markdown content.

        Args:
            content: A string containing the Markdown text.
        """
        self.content = content
        self.console = Console()

    def show(self):
        """
        Renders and displays the Markdown content in a pager.
        """
        # Using monokai for that classic, classy code look.
        markdown = Markdown(self.content, code_theme="monokai")
        with self.console.pager(styles=True):
            self.console.print(markdown)
