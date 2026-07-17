import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# main.py가 있는 루트 경로를 에이전트 탐색 경로로 지정
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ADK의 최신 FastAPI 헬퍼로 웹 서비스 생성
app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,  # ADK Web UI 활성화
)

if __name__ == "__main__":
    # Cloud Run이 제공하는 PORT 환경변수 또는 로컬의 8080 포트 바인딩
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
