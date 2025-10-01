# Zoo Tour Guide Agent & MCP Server Codelabs

This two-part codelab series guides you through building a complete, tool-using AI agent system on Google Cloud. You will start by creating and deploying a secure Model Context Protocol (MCP) server, which acts as a "tooling layer." Then, you will build and deploy an AI agent using the Agent Development Kit (ADK) that acts as the "reasoning layer," securely consuming the tools provided by your MCP server.

**❗️ Important:** This repository contains the source code for the **agent** built in **Lab 2**, located in the `/zoo_guide_agent` directory. You must complete Lab 1 to create and deploy the MCP server that this agent connects to.

---

## [Lab 1: Deploying a MCP Server](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-deploy-a-secure-mcp-server-on-cloud-run#0?utm_campaign=CDR_0xf9030db1_awareness_b448506025&utm_medium=external&utm_source=blog)

In this lab, you'll build and deploy a Model Context Protocol (MCP) server using FastMCP. This server will provide a secure, production-ready service on Cloud Run that exposes tools for an AI to use. You'll create a `zoo` server with two tools: `get_animals_by_species` and `get_animal_details`.

### What you'll learn
* How to deploy an MCP server to Cloud Run.
* How to secure your server's endpoint by requiring authentication, ensuring only authorized clients can communicate with it.
* How to connect to your secure MCP server from the Gemini CLI.

➡️ **Ready to build your secure tool server? [Start Lab 1 Now!](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-deploy-a-secure-mcp-server-on-cloud-run#0?utm_campaign=CDR_0xf9030db1_awareness_b448506025&utm_medium=external&utm_source=blog)**

---

## [Lab 2: Building and Deploying a Tour Guide Agent with ADK](https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent#0?utm_campaign=CDR_0xf9030db1_awareness_b448506025&utm_medium=external&utm_source=blog)

This lab focuses on building and deploying the client agent service. Using the Agent Development Kit (ADK), you will build a "zoo tour guide" AI agent. This agent demonstrates the key architectural principle of separating concerns: the agent (reasoning) communicates with the MCP server (tooling) via a secure API. The agent will use the tools from Lab 1, plus Wikipedia, to create the best tour guide experience. Finally, you will deploy the agent to Google Cloud Run so it can be accessed by all zoo visitors.

### What you'll learn
* How to structure a Python project for ADK deployment.
* How to implement a tool-using agent with the `google-adk`.
* How to connect an agent to a remote MCP server for its toolset.
* How to deploy a Python application as a serverless container to Cloud Run.
* How to configure secure, service-to-service authentication using IAM roles.
* How to delete Cloud resources to avoid incurring future costs.

🚀 **With your tool server ready, it's time to bring your agent to life. [Begin Lab 2 and build your tour guide!](https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent#0?utm_campaign=CDR_0xf9030db1_awareness_b448506025&utm_medium=external&utm_source=blog)**