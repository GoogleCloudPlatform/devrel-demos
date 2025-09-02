# MDView Test Document

This is a test document for `mdview`. It contains various Markdown elements to ensure everything renders correctly.

## Text Formatting

Here is some **bold text**, some *italic text*, and some `inline code`.

## Lists

An unordered list:
*   Item 1
*   Item 2
    *   Sub-item 2.1
*   Item 3

A numbered list:
1.  First item
2.  Second item
3.  Third item

## Code Block

This is a Python code block that should be syntax highlighted. It's intentionally long to test the pagination feature.

```python
import sys

class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self, loud=False):
        if loud:
            print(f'HELLO, {self.name.upper()}!')
        else:
            print(f'Hello, {self.name}')

def fibonacci(n):
    """
    Generates the Fibonacci sequence up to n.
    This is a classic example used in many programming tutorials.
    """
    a, b = 0, 1
    while a < n:
        print(a, end=' ')
        a, b = b, a+b
    print()

# Let's add more lines to ensure pagination kicks in.
# Line 1
# Line 2
# Line 3
# Line 4
# Line 5
# Line 6
# Line 7
# Line 8
# Line 9
# Line 10
# Line 11
# Line 12
# Line 13
# Line 14
# Line 15
# Line 16
# Line 17
# Line 18
# Line 19
# Line 20
# Line 21
# Line 22
# Line 23
# Line 24
# Line 25
# Line 26
# Line 27
# Line 28
# Line 29
# Line 30
```

## The End

If you can see this, you probably scrolled! Success!
