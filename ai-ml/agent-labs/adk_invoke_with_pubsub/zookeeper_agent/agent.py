import os

from google.adk.agents import Agent
from .tools import animal_species_tool, animal_list_tool, animals_by_species_tool, animal_details_tool
from .metadata import get_model_id

weather_agent = Agent(
    name = 'zookeeper_agent',
    model = get_model_id(),
    description = 'Your friendly zoo-keeper to answer your questions about animals in the zoo.',
    instruction = f"""
    You are a zoo-keeper. You primary function is to help users to find info about animals in zoo.

    *  Use the 'animal_species_tool' tool to get a list of all species.
    *  Use the 'animal_list_tool' tool to get names of all animals.
    *  Use the 'animals_by_species_tool' tool to get dictionary of all animals per provided species.
    *  Use the 'animal_details_tool' tool to get all information about a specific animal.

    If one of the tools returns an error or cannot provide results, inform the user politely.
    Handle only weather requests for a place of interest. Politely respond if the user asks for something else.
    """,
    tools=[animal_species_tool, animal_list_tool, animals_by_species_tool, animal_details_tool],
    output_key='zookeeper_response',
)

root_agent = weather_agent
