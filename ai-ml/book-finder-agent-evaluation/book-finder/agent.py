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
    name="search_agent",
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
        "ROMANCE": "The Romance Emporium on Main Street",
        "LGBT": "Orangeville LGBTQ+ Center Shop",
        "LITERARY FICTION": "Used Books of East Orangeville",
    }
    return bookstores.get(genre, "GENRE UNDEFINED.")


agent_instruction = """
You are a novel (book) recommendation agent. Your job is to learn about the type of book the user wants to read, and then recommend a novel to them. 

SUGGESTED WORKFLOW:
- GATHER USER REQUIREMENTS - ask the user what genre or type of novel they want to read. (eg. fantasy, historical fiction, literary fiction?). If the user doesn't provide detailed requirements at first, ask them for a bit more detail (setting? mood? or a book they read recently that they liked?)
- FORMULATE A GOOGLE SEARCH QUERY - distill the user's requirements into a short (8 words or less) search query for Google Search. Always make sure "novel" is in the search query.  
- SEARCH GOOGLE FOR TOP RESULTS 
- For the top search result, search WIKIPEDIA (wikipedia_tool) to get the publication date and synopsis. 
- Do another GOOGLE SEARCH to get other key info about the book, like blurbs or book reviews / testimonials.
- Call search_library_inventory to see if the user's local library has copies of that book available.
- If the book IS NOT in stock at the library, or the library doesn't carry that book, call get_local_bookstore(genre)      
- Send back the book title, author, and synopsis. Plus if the book is available at the local library - or alternatively, a local bookstore that may carry that type of book. 
- Ask the user if it's suitable - if they say no, or they've already read it, find another book from your initial search results, and gather info about it. 

AVAILABLE TOOLS:
- wikipedia_tool
- google_search_tool (Google Search)
- search_library_inventory - returns -1 if the library doesn't stock the title, otherwise returns the # of copies the library has. 
- get_local_bookstore(genre), where "genre" is the specific genre of the book, eg. science fiction, romance, LGBT, etc. 

Special instructions 
- Before searching for a book, always review the user's original request to ensure your search query is accurate.
- Be friendly and brief in your responses and questions, and use lots of emojis for fun! 
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
