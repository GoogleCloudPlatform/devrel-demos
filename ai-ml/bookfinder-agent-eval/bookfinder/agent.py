from google.adk.agents import Agent
from typing import Dict


def search_local_library(title: str) -> Dict[str, any]:
    """
    Searches the Orangeville Public Library system for a book.

    Args:
        title: The title of the book to search for.

    Returns:
        A dictionary with availability information including copies available and branch locations.
    """
    title = title.upper()

    inventory = {
        "THE LONG WAY TO A SMALL, ANGRY PLANET": {
            "copies": 1,
            "branch": "Orangeville Central Library",
            "available": True,
        },
        "HEARTSTOPPER": {
            "copies": 0,
            "branch": "Orangeville Central Library",
            "available": False,
        },
        "PRIDE AND PREJUDICE": {
            "copies": 0,
            "branch": "Orangeville Central Library",
            "available": False,
        },
        "STORIES OF YOUR LIFE AND OTHERS": {
            "copies": 2,
            "branch": "Orangeville North Branch",
            "available": True,
        },
        "THE BLUEST EYE": {
            "copies": 3,
            "branch": "Orangeville Central Library",
            "available": True,
        },
        "THERE THERE": {
            "copies": 4,
            "branch": "Orangeville South Branch",
            "available": True,
        },
        "1984": {
            "copies": 2,
            "branch": "Orangeville Central Library",
            "available": True,
        },
        "TO KILL A MOCKINGBIRD": {
            "copies": 6,
            "branch": "Orangeville Central Library",
            "available": True,
        },
    }

    if title in inventory:
        return inventory[title]
    else:
        return {
            "copies": 0,
            "branch": None,
            "available": False,
            "message": "Book not found in library system",
        }


def find_local_bookstore(genre: str) -> Dict[str, any]:
    """
    Finds local bookstores in Orangeville that specialize in a specific genre.

    Args:
        genre: The genre of the book (e.g., "science fiction", "romance", "mystery").

    Returns:
        A dictionary with bookstore information that may carry books in that genre.
    """
    genre = genre.upper()

    bookstores_by_genre = {
        "SCIENCE FICTION": {
            "store_name": "Galaxy Books Orangeville",
            "address": "123 Main Street, Downtown Orangeville",
            "phone": "(555) 555-7827",
            "specialties": "Science fiction, fantasy, and speculative fiction",
            "note": "Best selection of sci-fi in town",
        },
        "FANTASY": {
            "store_name": "Galaxy Books Orangeville",
            "address": "123 Main Street, Downtown Orangeville",
            "phone": "(555) 554-7110",
            "specialties": "Science fiction, fantasy, and speculative fiction",
            "note": "Extensive fantasy collection including rare editions",
        },
        "ROMANCE": {
            "store_name": "The Paper Heart Bookshop",
            "address": "456 Broadway Avenue, Orangeville",
            "phone": "(555) 555-5683",
            "specialties": "Romance, contemporary fiction, and women's literature",
            "note": "Romance book club meets Thursdays",
        },
        "MYSTERY": {
            "store_name": "Mystery Manor Books",
            "address": "789 First Street, Old Town Orangeville",
            "phone": "(555) 555-2663",
            "specialties": "Mystery, thriller, crime, and detective fiction",
            "note": "Ask about their mystery box subscription",
        },
        "THRILLER": {
            "store_name": "Mystery Manor Books",
            "address": "789 First Street, Old Town Orangeville",
            "phone": "(555) 555-2663",
            "specialties": "Mystery, thriller, crime, and detective fiction",
            "note": "New thrillers arrive every Tuesday",
        },
        "LITERARY FICTION": {
            "store_name": "Chapter & Verse Books",
            "address": "321 Mill Street, Orangeville Arts District",
            "phone": "(555) 555-7378",
            "specialties": "Literary fiction, classics, and poetry",
            "note": "Curated selection by local book critics",
        },
        "NON-FICTION": {
            "store_name": "BookHaven Orangeville",
            "address": "246 Centre Street, Downtown Orangeville",
            "phone": "(555) 555-2665",
            "specialties": "General bookstore with strong non-fiction section",
            "note": "Can special order any title",
        },
        "BIOGRAPHY": {
            "store_name": "BookHaven Orangeville",
            "address": "246 Centre Street, Downtown Orangeville",
            "phone": "(555) 551-2665",
            "specialties": "General bookstore with strong non-fiction section",
            "note": "Extensive biography and memoir collection",
        },
        "HISTORY": {
            "store_name": "The Historical Page",
            "address": "159 Heritage Way, Old Town Orangeville",
            "phone": "(555) 552-4478",
            "specialties": "History, military history, and local history",
            "note": "Specializes in world history",
        },
    }

    if genre in bookstores_by_genre:
        return bookstores_by_genre[genre]
    else:
        return "I can't find a bookstore that serves that genre of book, sorry!"


def order_online(title: str) -> Dict[str, any]:
    """
    Provides online ordering options for a physical book.

    Args:
        title: The title of the book to order.

    Returns:
        A dictionary with online ordering information for physical books.
    """
    return {
        "title": title,
        "online_retailers": [
            {
                "name": "MapleLeaf Books Online",
                "estimated_delivery": "2-3 business days",
                "price_range": "$18-35",
                "shipping": "Free shipping over $35",
                "note": "Woman-owned and operated",
            },
            {
                "name": "BookStream Orangeville",
                "estimated_delivery": "3-5 business days",
                "price_range": "$15-32",
                "shipping": "$4.99 flat rate shipping",
                "note": "Rewards program available",
            },
            {
                "name": "The Reading Post",
                "estimated_delivery": "4-7 business days",
                "price_range": "$12-28",
                "shipping": "Free shipping on all orders",
                "note": "Discount retailer with overstock books",
            },
        ],
        "special_order_option": {
            "service": "BookHaven Orangeville Special Orders",
            "phone": "(555) 555-2665",
            "estimated_time": "5-10 business days",
            "note": "Support local business - they can order any book in print",
        },
        "recommendation": "Consider calling BookHaven Orangeville first for special orders to support local business.",
    }


agent_instruction = """
You are a book finder agent for Orangeville residents. 📚 Your job is to help users find the fastest way to get a specific book they want.

---

### **Workflow**

**STEP 1: UNDERSTAND THE REQUEST**
* Extract the book title from the user's request.
* If the user doesn't provide a specific title, ask them which book they're looking for.

**STEP 2: FIND THE BOOK (IN PRIORITY ORDER)**
1. **Check Local Library First:** Use `search_local_library` to check if the Orangeville Public Library has the book.
   - If available (copies > 0), provide the branch location and number of copies.
   
2. **Check Local Bookstores:** If not available at the library, use `find_local_bookstore` with the book's genre to find bookstores that may carry it.
   - Provide the store name, address, and contact info.
   - Suggest calling ahead to confirm availability.
   
3. **Online Options:** As a last resort, use `order_online` to provide online ordering options.
   - Find the option with the fastest delivery.
   - Offer a local bookstore option as a special order through BookHaven Orangeville.


**STEP 3: PRESENT THE FASTEST OPTION**
* Clearly state the fastest way to get the book.
* Provide all relevant details (location, availability, contact info).
* If multiple options exist, list them in order of speed/convenience.
* Always prioritize local options over online when available.

---

### **Available Tools**
* `search_local_library` - Check Orangeville Public Library system
* `find_local_bookstore` - Find local bookstores by genre that may have the book
* `order_online` - Provide online ordering options for physical books

---

### **Special Instructions**
* **Be helpful and efficient.** Focus on getting the book quickly.
* **Prioritize local options** to support the Orangeville community.
* **Use emojis** for fun. 
* **Respond in complete sentences.
* **Be friendly and brief** in your responses! 🏪📖
"""

agent = Agent(
    model="gemini-2.5-pro",
    name="book_finder",
    instruction=agent_instruction,
    tools=[
        search_local_library,
        find_local_bookstore,
        order_online,
    ],
)

root_agent = agent
