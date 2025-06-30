import os
import sys
sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response

from dotenv import load_dotenv
from datetime import datetime, timedelta
import dateparser

from google.adk import Agent

load_dotenv()
model_name = os.getenv("MODEL")


def get_date(x_days_from_today:int):
    """
    Retrieves a date for today or a day relative to today.

    Args:
        x_days_from_today (int): how many days from today? (use 0 for today)

    Returns:
        A dict with the date in a formal writing format. For example:
        {"date": "Wednesday, May 7, 2025"}
    """

    target_date = datetime.today() + timedelta(days=x_days_from_today)
    date_string = target_date.strftime("%A, %B %d, %Y")

    return {"date": date_string}

def write_journal_entry(entry_date:str, journal_content:str):
    """
    Writes a journal entry based on the user's thoughts.

    Args:
        entry_date (str): The entry date of the journal entry)
        journal_content (str): The body text of the journal entry

    Returns:
        A dict with the filename of the written entry. For example:
        {"entry": "2025-05-07.txt"}
        Or a dict indicating an error, For example:
        {"status": "error"}
    """

    date_for_filename = dateparser.parse(entry_date).strftime("%Y-%m-%d")
    filename = f"{date_for_filename}.txt"
    
    # Create the file if it doesn't already exist
    if not os.path.exists(filename):
        print(f"Creating a new journal entry: {filename}")
        with open(filename, "w") as f:
            f.write("### " + entry_date)

    # Append to the dated entry
    try:
        with open(filename, "a") as f:
            f.write("\n\n" + journal_content)            
        return {"entry": filename}
    except:
        return {"status": "error"}

root_agent = Agent(
    name="function_tool_agent",
    model=model_name,
    description="Help users practice good daily journalling habits.",
    instruction="""
    Ask the user how their day is going and
    use their response to write a journal entry for them.""",
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,
    # Add the function tools below
    tools=[get_date, write_journal_entry]
)