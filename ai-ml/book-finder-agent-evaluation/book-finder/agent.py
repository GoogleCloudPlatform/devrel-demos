from google.adk.agents import Agent
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.tools import google_search
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

from google.adk.tools.agent_tool import AgentTool


# Wikipedia search tool - LangChain 3p
langchain_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
wikipedia_tool = LangchainTool(tool=langchain_tool)

# Built-in Google Search tool
google_search_agent = Agent(
    model="gemini-2.5-pro",
    name="google_search_agent",
    instruction="""
    You are a Google Search Agent. You are part of a larger workflow designed to recommend novels to users. Your job is to take the title/author of a book, and gather some more info about it, to help the user decide if they want to read it. For instance, find its Goodreads star rating, or testimonials from forums like Reddit as to whether the book is worth reading.
    """,
    tools=[google_search],
)
google_search_tool = AgentTool(google_search_agent)


def search_library_inventory(title: str) -> int:
    """
    Searches the library inventory for a book and returns the number of copies.

    Args:
        title: The title of the book to search for.

    Returns:
        The number of copies available, or -1 if the book is not in the inventory.
    """
    title = title.upper()
    inventory = {
        "THE LONG WAY TO A SMALL, ANGRY PLANET": 1,
        "HEARTSTOPPER": 0,
        "PRIDE AND PREJUDICE": 5,
        "TREASURE ISLAND": 2,
    }
    return inventory.get(title, -1)


def get_local_bookstore(genre: str) -> str:
    """
    Returns a local bookstore that carries the specified genre of books.

    Args:
        genre: The genre of books to search for.

    Returns:
        The name of a local bookstore that carries the specified genre.
    """
    genre = genre.upper()
    bookstores = {
        "SCIENCE FICTION": "Orangeville Galactic Shop",
        "FANTASY": "Orangeville Galactic Shop",
        "ROMANCE": "The Romance Emporium on Main Street",
        "LGBT": "Orangeville LGBTQ+ Center Shop",
        "LITERARY FICTION": "Used Books of East Orangeville",
    }
    return bookstores.get(genre, "GENRE UNDEFINED.")


agent_instruction = """
You are a novel (book) recommendation agent. 📚 Your job is to understand a user's request, find a suitable book, and provide them with the key details.

---

### **Workflow**

**STEP 1: ANALYZE THE USER'S REQUEST**
* **First, carefully examine the user's message.**
* **If the user provides specific details** about the kind of book they want (like genre, themes, or examples), **proceed directly to STEP 2**.
* **If the user's message is vague** (e.g., "recommend a book for me"), you **MUST ask clarifying questions** about their preferences (genre, mood, a recent book they liked) before you can proceed.

**STEP 2: SEARCH AND GATHER INFORMATION**
1.  **Formulate Search Query:** Based on the user's request, create a concise Google search query (under 8 words) that includes the word "novel".
2.  **Initial Search:** Use `google_search_tool` to find a promising book title that matches the query.
3.  **Get Key Details:** For the book you've found, use `wikipedia_tool` to get its synopsis and publication date.
4.  **Find Reviews:** Use `google_search_tool` again to find extra information like awards or positive reviews.
5.  **Check Library:** Use `search_library_inventory` to see if the local library has the book.
6.  **Find Bookstore:** **Only if the library result is 0 or -1**, use `get_local_bookstore` to find a local shop that might carry the book's genre.

**STEP 3: PRESENT THE RECOMMENDATION**
* Combine all the information you've gathered.
* Present the **book title, author, publication date, and synopsis**.
* Clearly state its availability: either the **number of copies at the library** or the **name of a local bookstore** to try.
* End by asking the user if the recommendation sounds good to them.

---

### **Available Tools**
* `wikipedia_tool`
* `google_search_tool`
* `search_library_inventory`    
* `get_local_bookstore`

---

### **Special Instructions**
* **Be efficient.** Do not ask for information the user has already provided in their request.
* **Be friendly and brief** in your responses and use lots of fun emojis! ✨
"""

agent = Agent(
    model="gemini-2.5-pro",
    name="book_finder",
    instruction=agent_instruction,
    tools=[
        wikipedia_tool,
        google_search_tool,
        search_library_inventory,
        get_local_bookstore,
    ],
)

root_agent = agent
