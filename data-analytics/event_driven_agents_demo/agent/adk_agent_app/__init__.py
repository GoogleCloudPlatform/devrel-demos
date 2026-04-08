"""
This file marks the 'adk_agent_app' directory as a Python package.

By importing the modules below, it makes them attributes of the package itself.
This allows other scripts (like the main application runner) to access the agent
definitions more cleanly. For example, it allows importing the agent module by writing:
  from adk_agent_app import agent
instead of having to target the specific file:
  from adk_agent_app.agent import ...
"""

# Perform a relative import to expose the 'agent.py' module.
# This makes all agent definitions (like 'decision_agent') and the
# 'get_root_agent' function accessible via the 'adk_agent_app' package.
from . import agent