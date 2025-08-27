from setuptools import setup

# It's good practice to have a long description from a README file.
with open("user_guide.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mdview",
    version="0.1.0",
    author="K-bro & Gemini",
    description="A simple, elegant command-line Markdown viewer.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=['viewer'],  # We have a single module, not a package.
    install_requires=[
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "mdview=mdview:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
