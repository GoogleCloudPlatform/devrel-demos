"""Personal Tech-Briefing Digest Agent.

Built with Google Agent Development Kit 2.0 and deployable to Google Cloud Run Instances.
"""

from digest_agent.agent import root_agent
from digest_agent.server import app

__all__ = ["root_agent", "app"]
