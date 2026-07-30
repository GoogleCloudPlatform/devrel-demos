# Copyright 2026 Google LLC
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

import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agent import create_graph_agent

async def main():
    agent = create_graph_agent()
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    session_id = "cli_session"
    print("🤖 Spanner & BigQuery Knowledge Graph Agent initialized.")
    print("Type your question (e.g. 'Which customers filed complaints on products containing Fiberglass?') or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                break
            
            print("\nThinking...")
            response = await runner.run(
                session_id=session_id,
                user_message=user_input
            )
            print(f"\nAgent: {response.text}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    asyncio.run(main())
