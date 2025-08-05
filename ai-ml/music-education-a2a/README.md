# 🎻 Music Education Multi-Agent with ADK and A2A 🎼

## Run Locally

**Prerequisites**: 
- A terminal with Python 3.10+ installed  
- uv (Python package manager)
- [ffmpeg](https://ffmpeg.org/) (eg. `brew install ffmpeg`)

**Run the Historical Context Agent (`RemoteA2AAgent`)** 

Rather than running this in the ADK Web UI or with an interactive runner, we'll run this helper agent as a backend *API server* that our root Music Education Agent can call. 

```bash
uvicorn historical_context_agent:a2a_app --host localhost --port 8001
```

**Verify that the Agent Card is available over Localhost**: 


**[Optional] Run the A2A Inspector**: 

```bash
git clone https://github.com/a2aproject/a2a-inspector.git
cd a2a-inspector
uv sync
cd frontend
npm install
cd ..
chmod +x run.sh
./run.sh
```

**Run the Music Education Agent**: 

In another terminal tab, from the `music-education-a2a` root directory: 

```bash
uv run adk web
```

**Test prompts:**
- Dvorak 9th Symphony 2nd movement 
- Rachmaninov 2nd piano concerto 1st movement
- Brahms 3rd Symphony 3rd movement
- Bach - Goldberg Variations
- Mozart Sinfonia Concertante in E flat
- Mahler Symphony no. 2 finale
- Wagner Tristan und Isolde
- Sibelius Symphony no. 2 

... Or any piece you want to learn more about! 

## Run in Google Cloud 

TODO 