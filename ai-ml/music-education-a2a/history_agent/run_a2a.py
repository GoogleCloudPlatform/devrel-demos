# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A2A Server that acts as a proxy in front of an ADK agent"""

import logging
from typing import Any,Dict, Callable, Optional
from typing_extensions import override

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import TaskStore, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.types import (
    AgentCard,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    DEFAULT_RPC_URL,
)

from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.agents import BaseAgent
from google.adk.artifacts import BaseArtifactService
from google.adk.memory import BaseMemoryService
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService


from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import JSONResponse

from vertexai.preview import reasoning_engines


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ADKExecutor(A2aAgentExecutor):
    """Executes the ADK agent logic in response to A2A requests."""

    def __init__(
        self,
        adk_agent: BaseAgent,
        task_store: TaskStore,
        session_service_builder: Optional[Callable[..., "BaseSessionService"]] = None,
        artifact_service_builder: Optional[Callable[..., "BaseArtifactService"]] = None,
        memory_service_builder: Optional[Callable[..., "BaseMemoryService"]] = None,
        enable_tracing: Optional[bool] = False,
        env_vars: Optional[Dict[str, str]] = None,
    ):
        super().__init__(runner=self.create_runner)
        self.adk_agent = adk_agent
        self.task_store = task_store
        # We borrow a runner from AdkApp,
        # mostly to not rewrite what's in its set_up function.
        self.adk_app = reasoning_engines.AdkApp(
            agent=adk_agent,
            enable_tracing=enable_tracing or False,
            session_service_builder=session_service_builder,
            artifact_service_builder=artifact_service_builder,
            memory_service_builder=memory_service_builder,
            env_vars=env_vars
        )
        self.adk_runner = None
        self.setup = False

    async def create_runner(self) -> Runner:
        if not self.setup:
            self.setup = True
            self.adk_app.set_up()
        if (
            not hasattr(self.adk_app, "_tmpl_attrs")
            or not isinstance(self.adk_app._tmpl_attrs, Dict)
            or "runner" not in self.adk_app._tmpl_attrs
            or not isinstance(self.adk_app._tmpl_attrs["runner"], Runner)
        ):
            raise RuntimeError(
                "This code is incompatible with AdkApp implementation"
            )
        return self.adk_app._tmpl_attrs["runner"]



class A2AStarletteApplicationWithHost(A2AStarletteApplication):
    """This class makes sure the agent's url in the AgentCard has the same
    host, port and schema as in the request.
    """

    @override
    def build(
            self,
            agent_card_url: str = AGENT_CARD_WELL_KNOWN_PATH,
            rpc_url: str = DEFAULT_RPC_URL,
            **kwargs: Any,
        ) -> Starlette:
        self.rpc_url = rpc_url
        self.card_url = agent_card_url
        return super().build(
            agent_card_url=agent_card_url,
            rpc_url=rpc_url,
            **kwargs
        )


    @override
    async def _handle_get_agent_card(self, request: Request) -> JSONResponse:
        """Handles GET requests for the agent card endpoint.

        Args:
            request: The incoming Starlette Request object.

        Returns:
            A JSONResponse containing the agent card data.
        """
        port = None
        if "X-Forwarded-Host" in request.headers:
            host = request.headers["X-Forwarded-Host"]
        else:
            host = request.url.hostname
            port = request.url.port
        if "X-Forwarded-Proto" in request.headers:
            scheme = request.headers["X-Forwarded-Proto"]
        else:
            scheme = request.url.scheme
        if not scheme:
            scheme = "http"
        if ":" in host: # type: ignore
            comps = host.rsplit(":", 1) # type: ignore
            host = comps[0]
            port = comps[1]

        path = ""
        if "X-Forwarded-Path" in request.headers:
            path = request.headers["X-Forwarded-Path"].strip()
            if (path
                and path.lower().endswith(self.card_url.lower())
                and len(path) - len(self.card_url) > 1
            ):
                path = path[:-len(self.card_url)].rstrip("/") + self.rpc_url
        else:
            path = self.rpc_url

        card = self.agent_card.model_copy()
        source_parsed = URL(card.url)
        if port:
            card.url = str(
                source_parsed.replace(
                    hostname=host,
                    port=port,
                    scheme=scheme,
                    path=path
                )
            )
        else:
            card.url = str(
                source_parsed.replace(
                    hostname=host,
                    scheme=scheme,
                    path=path
                )
            )

        return JSONResponse(
            card.model_dump(mode='json', exclude_none=True)
        )



def adk_as_a2a(
        adk_agent: BaseAgent,
        enable_tracing: Optional[bool] = False,
        session_service_builder: Optional[Callable[..., "BaseSessionService"]] = None,
        artifact_service_builder: Optional[Callable[..., "BaseArtifactService"]] = None,
        memory_service_builder: Optional[Callable[..., "BaseMemoryService"]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        a2a_agent_version: Optional[str] = None,
        agent_card_url_path: str = AGENT_CARD_WELL_KNOWN_PATH,
        agent_rpc_path: str = DEFAULT_RPC_URL,
        override_agent_card: Optional[AgentCard] = None,
        task_store: TaskStore = InMemoryTaskStore(),
    ) -> Starlette:
    """Runs an ADK agent as an A2A server in Starlette

    Args:
        adk_agent (BaseAgent): ADK Agent
        enable_tracing (bool, optional): Enable Tracing. Defaults to False.
        session_service_builder (Callable[..., BaseSessionService], optional):
            Function to call to create a session service for the agent. Defaults to None.
        artifact_service_builder (Callable[..., BaseArtifactService;], optional):
            Function to call to create a artifact service for the agent. Defaults to None.
        memory_service_builder: (Callable[..., "BaseMemoryService"], optional):
            Function to call to create a memory service for the agent. Defaults to None.
        env_vars (Dict[str, str], optional): Additional environment variables for the agent. Defaults to None.
        a2a_agent_version (str, optional): Agent Version. Defaults to None.
        agent_card_url_path (str, optional): Agent Card path. Defaults to AGENT_CARD_WELL_KNOWN_PATH.
        agent_rpc_path (str, optional): Agent RPC path. Defaults to DEFAULT_RPC_URL.
        override_agent_card (AgentCard, optional): AgentCard to use instead of generating one from the ADK agent. Defaults to None.
        task_store (TaskStore, optional): A2A Task Store to use Defaults to InMemoryTaskStore().

    Returns:
        Starlette: Starlette application
    """

    logger.info(f"Configuring A2A server for agent `{adk_agent.name}`...")

    if override_agent_card:
        # Agent Url is dynamic later in A2AStarletteApplicationWithHost
        agent_card = override_agent_card.model_copy()
    else:
        if hasattr(adk_agent, "input_schema"):
            default_input_mode = "application/json"
        else:
            default_input_mode = "text"
        if hasattr(adk_agent, "output_schema"):
            default_output_mode = "application/json"
        else:
            default_output_mode = "text"
        try:
            agent_card = AgentCard(
                name=adk_agent.name,
                description=adk_agent.description,
                # Url is dynamic later in A2AStarletteApplicationWithHost
                url="http://127.0.0.1",
                version=a2a_agent_version or "0.0.1",
                capabilities=AgentCapabilities(
                    streaming=True,
                    push_notifications=False, # Not implemented
                ),
                skills=[
                    AgentSkill(
                        id=adk_agent.name,
                        name=adk_agent.name,
                        description=adk_agent.description,
                        tags=["adk_as_a2a"],
                    )
                ],
                default_input_modes=[
                    default_input_mode
                ],
                default_output_modes=[default_output_mode],
            )
        except Exception:
            logger.exception("Error creating AgentCard")
            raise

    try:
        agent_executor = ADKExecutor(
            adk_agent=adk_agent,
            task_store=task_store,
            session_service_builder=session_service_builder,
            artifact_service_builder=artifact_service_builder,
            memory_service_builder=memory_service_builder,
            enable_tracing=enable_tracing,
            env_vars=env_vars,
        )
    except Exception:
        logger.exception("Error initializing agent executor")
        raise

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store
    )
    try:
        app = A2AStarletteApplicationWithHost(
            agent_card=agent_card,
            http_handler=request_handler,
        ).build(
            agent_card_url=agent_card_url_path,
            rpc_url=agent_rpc_path
        )
        logger.info(f"{adk_agent.name} A2A server app is ready.")
        return app

    except Exception:
        logger.exception("Error initializing A2AStarletteApplication")
        raise

