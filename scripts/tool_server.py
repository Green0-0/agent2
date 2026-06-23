import argparse
import os
import subprocess
import sys
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent2.tool_api.api_helpers.custom_handler import (
    handle_build_call,
    handle_build_response,
    handle_build_schema,
    handle_convert,
    handle_extract,
    handle_parse_roundtrip,
    handle_validate,
)
from agent2.tool_api.api_helpers.history import get_history_store
from agent2.tool_api.api_helpers.openai_proxy import proxy_openai_request
from agent2.tool_api.api_helpers.pipeline_factory import build_pipeline

def create_app(
    backend_url: str,
    pipeline_format: str = "xml",
    schema_key: str = "{{llm_tools_list}}",
    replace_schema_all: bool = True,
) -> FastAPI:
    app = FastAPI(title="Tool API Proxy", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    pipeline = build_pipeline(
        pipeline_format,
        schema_key=schema_key,
        replace_schema_all=replace_schema_all,
    )
    history = get_history_store()

    app.state.pipeline = pipeline
    app.state.backend_url = backend_url
    app.state.history = history

    @app.on_event("startup")
    async def startup_event():
        # Reuse a single AsyncClient for all proxied requests
        app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))

    @app.on_event("shutdown")
    async def shutdown_event():
        await app.state.http_client.aclose()

    custom_routes = {
        "convert": handle_convert,
        "extract": handle_extract,
        "build_schema": handle_build_schema,
        "build_call": handle_build_call,
        "build_response": handle_build_response,
        "validate": handle_validate,
        "roundtrip": handle_parse_roundtrip,
    }

    @app.get("/")
    async def root():
        return {
            "service": "tool-api-proxy",
            "backend": backend_url,
            "format": pipeline_format,
            "custom_endpoints": list(custom_routes.keys()),
            "ui_endpoints": ["/custom/history", "/custom/stats"],
        }

    @app.get("/custom/history")
    async def get_history(endpoint: Optional[str] = None, limit: int = 100):
        return history.get_records(endpoint=endpoint, limit=limit)

    @app.get("/custom/stats")
    async def get_stats(endpoint: Optional[str] = None):
        return history.get_stats(endpoint=endpoint)

    @app.post("/custom/clear")
    async def clear_history():
        history.clear()
        return {"success": True}

    @app.api_route(
        "/custom/{action}",
        methods=["POST"],
    )
    async def custom_dispatch(action: str, request: Request):
        if action in custom_routes:
            return await custom_routes[action](request, pipeline, history)
        return JSONResponse(
            {"success": False, "error": f"Unknown custom action: {action}"},
            status_code=404,
        )

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    async def openai_proxy(path: str, request: Request):
        return await proxy_openai_request(
            request, backend_url, pipeline, history, path, request.app.state.http_client
        )

    return app

def _run_streamlit_subprocess(server_port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["TOOL_API_URL"] = f"http://localhost:{server_port}"
    here = os.path.dirname(os.path.abspath(__file__))
    webui_path = os.path.join(here, "webui.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", webui_path,
        "--server.headless", "true",
    ]
    return subprocess.Popen(cmd, env=env)

def main():
    parser = argparse.ArgumentParser(description="Tool API Proxy Server")
    parser.add_argument(
        "--backend-url", required=True,
        help="Backend URL that OpenAI requests are forwarded to (e.g., http://localhost:11434)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--format", default="xml", choices=["xml", "json", "md", "fake_codeact"], help="Tool format: xml, json, md, fake_codeact")
    parser.add_argument(
        "--schema-key", default="{{llm_tools_list}}",
        help="Token in prompts replaced with the tool schema string",
    )
    parser.add_argument(
        "--no-replace-all", action="store_true",
        help="Only replace schema key in system messages",
    )
    parser.add_argument(
        "--webui", action="store_true",
        help="Launch the Streamlit WebUI alongside the API",
    )
    args = parser.parse_args()

    app = create_app(
        backend_url=args.backend_url,
        pipeline_format=args.format,
        schema_key=args.schema_key,
        replace_schema_all=not args.no_replace_all,
    )

    if args.webui:
        _run_streamlit_subprocess(args.port)

    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()