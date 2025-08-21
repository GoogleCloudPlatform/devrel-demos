from google.adk.agents import Agent
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.tools import google_search
from langchain_community.tools.google_books import GoogleBooksQueryRun
from langchain_community.utilities.google_books import GoogleBooksAPIWrapper
from google.adk.tools.agent_tool import AgentTool

import os

# Init Google Books API connection via LangChain tool + ADK integration
google_books_api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
if not google_books_api_key:
    raise ValueError("GOOGLE_BOOKS_API_KEY environment variable is not set")
google_books_tool = GoogleBooksQueryRun(api_wrapper=GoogleBooksAPIWrapper())
google_books_langchain_tool = LangchainTool(google_books_tool)

# Built-in Google Search tool
search_agent = Agent(
    model="gemini-2.5-flash",
    name="search_agent",
    instruction="""
    You are a Google Search Agent. You are part of a larger workflow designed to recommend novels to users. Your job is to take the title/author of a book, and gather some more info about it, to help the user decide if they want to read it. For instance, find its Goodreads star rating, or testimonials from forums like Reddit as to whether the book is worth reading.
    """,
    tools=[google_search],
)

search_tool = AgentTool(search_agent)

agent_instruction = """
You are a novel (book) recommendation agent. Your job is to learn about the type of book the user wants to read, and then recommend a novel to them. 

SUGGESTED WORKFLOW:
- GATHER USER REQUIREMENTS - ask the user what genre or type of novel they want to read. (eg. fantasy, historical fiction, literary fiction?). If the user doesn't provide detailed requirements at first, ask them for a bit more detail (setting? mood? or a book they read recently that they liked?)
- FORMULATE A GOOGLE SEARCH QUERY - distill the user's requirements into a short (8 words or less) search query for Google Search. Always make sure "novel" is in the search query.  
- SEARCH GOOGLE FOR TOP RESULTS 
- For the top search result, search GOOGLE BOOKS to get the published synopsis. 
- Do another GOOGLE SEARCH to get other key info about the book, like blurbs or book reviews / testimonials.
- Send back the book title, author, synopsis, and any other key info you found. 
- Ask the user if it's suitable - if they say no, or they've already read it, find another book from your initial search results, and gather info about it. 

Special instructions - be brief in your responses and questions, and use lots of emojis for fun! 
"""

root_agent = Agent(
    model="gemini-2.5-flash",
    name="book_recommendations",
    instruction=agent_instruction,
    tools=[google_books_langchain_tool, search_tool],
)
