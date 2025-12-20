# Diagnostic Agent (TDC 2025 Demo)

_This project is a demonstration from [The Developer's Conference (TDC) São Paulo 2025](https://thedevconf.com/). It showcases a local diagnostic agent built with Gemini and osquery._

---

# Agente Diagnóstico com Gemini e osquery

Este projeto contém o código fonte para o agente de diagnósticos apresentado na talk [Como criar um agente de diagnósticos usando Gemini e Osquery](https://speakerdeck.com/danicat/como-criar-um-agente-de-diagnosticos-usando-gemini-e-osquery) apresentada no TDC São Paulo 2025.

_Nota da autora: o código neste projeto foi todo gerado por inteligência artificial usando a Gemini CLI. Embora eu tenha revisado o código para erros básicos, eu não me responsabilizo por quaisquer problemas gerados por esse código! Use por sua própria conta e risco!_

## Autenticação

Via API Key:

```sh
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
```

Via Vertex AI:

```sh
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=LOCATION
```

Se você estiver usando o Vertex AI, também vai precisar autenticar o seu usuário:

```sh
gcloud auth application-default login
```

## Versões

- v1: projeto inicial
- v2: system prompt melhorada
- v3: suporte a Google Search
- v4: suporte a RAG com schema das tabelas
- v5: suporte a live API (voz) com bidirecional streaming

## Scripts

- download_schema.py: faz download dos schemas do osquery a partir do GitHub (requer um personal access token)
- setup_rag.py: cria um RAG no Vertex AI a partir dos arquivos txt descrevendo os schemas. (requer um projeto GCP e uma location)