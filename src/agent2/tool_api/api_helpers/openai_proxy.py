import json
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from agent2.tool_api.api_helpers.history import HistoryRecord, HistoryStore, _err_to_str
from agent2.tool_api.abc.tool_pipeline import ToolPipeline

def _join_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path

def _filter_headers(headers) -> Dict[str, str]:
    """Filters out hop-by-hop headers to prevent proxy injection issues."""
    excluded = {"content-length", "transfer-encoding", "connection", "content-type"}
    return {k: v for k, v in headers.items() if k.lower() not in excluded}

async def proxy_openai_request(
    request: Request,
    backend_url: str,
    pipeline: ToolPipeline,
    history: HistoryStore,
    path: str,
    client: httpx.AsyncClient,
):
    """Forward an OpenAI-compatible request to the backend, performing
    tool-parse conversion on the way out and tool-call extraction on the way back.
    """
    start_time = time.time()

    # Non-JSON or non-POST requests: pass through unchanged.
    if request.method != "POST":
        return await _passthrough(request, backend_url, path, client)

    body_bytes = await request.body()
    if not body_bytes:
        return await _passthrough(request, backend_url, path, client, body=body_bytes)

    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    if not isinstance(body, dict) or "messages" not in body:
        # Not a chat completion - forward unchanged raw bytes.
        return await _passthrough(request, backend_url, path, client, body=body_bytes)

    is_stream_requested = bool(body.get("stream", False))
    errors: list = []
    schemas = body.get("tools")
    parsed_body: Optional[Dict[str, Any]] = None

    # ---- 1. Convert the inbound OAI chat to a tools-free chat ----
    try:
        parsed_body = pipeline.convert_openai(body)
    except Exception as e:
        msg = f"Request parse failed: {e}"
        errors.append(msg)
        _record_history(
            history, body, None, None, None,
            errors, start_time, success=False,
        )
        return JSONResponse({"error": msg}, status_code=400)

    # Always force non-stream on the upstream so we can safely extract tool calls
    forward_body = dict(parsed_body)
    forward_body["stream"] = False

    # Strip hop-by-hop headers and re-set content-type
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "connection", "transfer-encoding"}
    }
    headers["content-type"] = "application/json"

    # ---- 2. Forward to backend ----
    forward_url = _join_url(backend_url, path)
    try:
        backend_resp = await client.post(
            forward_url,
            content=json.dumps(forward_body),
            headers=headers,
        )
    except Exception as e:
        msg = f"Backend request failed: {e}"
        errors.append(msg)
        _record_history(
            history, body, parsed_body, None, None,
            errors, start_time, success=False,
        )
        return JSONResponse({"error": msg}, status_code=502)

    if backend_resp.status_code != 200:
        _record_history(
            history, body, parsed_body,
            {"status": backend_resp.status_code, "body": backend_resp.text},
            None, errors, start_time, success=False,
        )
        return Response(
            content=backend_resp.content,
            status_code=backend_resp.status_code,
            media_type=backend_resp.headers.get("content-type", "application/json"),
        )

    try:
        resp_json = backend_resp.json()
    except json.JSONDecodeError:
        # Non-JSON response - pass through.
        return Response(
            content=backend_resp.content,
            media_type=backend_resp.headers.get("content-type"),
            headers=_filter_headers(backend_resp.headers),
        )

    # ---- 3. Extract tool calls from the response ----
    extracted_messages = []
    for choice in resp_json.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        if isinstance(content, list):
            text_parts = [
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            content = "".join(text_parts)
        try:
            extracted_msg, raw_errs = pipeline.extract_response(content, schemas)
            errors.extend(_err_to_str(e) for e in raw_errs)
            
            # Fix OpenAI format: 'finish_reason' belongs on the choice, not the message
            finish_reason = extracted_msg.pop("finish_reason", "stop")
            msg.clear()
            msg.update(extracted_msg)
            
            extracted_messages.append(extracted_msg)
            choice["finish_reason"] = finish_reason
        except Exception as e:
            errors.append(f"Extraction error: {e}")
            extracted_messages.append(msg)

    _record_history(
        history, body, parsed_body, resp_json,
        extracted_messages[0] if extracted_messages else None,
        errors, start_time, success=len(errors) == 0,
    )

    # ---- 4. Return response (streaming or full) ----
    if is_stream_requested:
        return StreamingResponse(
            _simulate_stream(resp_json),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    return JSONResponse(resp_json)

async def _passthrough(
    request: Request,
    backend_url: str,
    path: str,
    client: httpx.AsyncClient,
    body: Optional[bytes] = None,
):
    """Forward a request unchanged (used for non-chat endpoints like /v1/models)."""
    url = _join_url(backend_url, path)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "connection", "transfer-encoding"}
    }
    data = body if body is not None else await request.body()
    
    backend_resp = await client.request(
        request.method, url, content=data, headers=headers
    )
    
    return Response(
        content=backend_resp.content,
        status_code=backend_resp.status_code,
        media_type=backend_resp.headers.get("content-type"),
        headers=_filter_headers(backend_resp.headers),
    )

def _record_history(
    history: HistoryStore,
    request_data: Any,
    parsed_data: Any,
    response_data: Any,
    extracted_response: Any,
    errors: list,
    start_time: float,
    success: bool,
) -> None:
    history.add(
        HistoryRecord(
            endpoint="openai",
            action=None,
            request_data=request_data,
            parsed_data=parsed_data,
            response_data=response_data,
            extracted_response=extracted_response,
            errors=errors,
            latency_ms=(time.time() - start_time) * 1000.0,
            success=success,
        )
    )

async def _simulate_stream(resp_json: Dict[str, Any]):
    """Convert a non-streamed chat-completion response into an SSE stream."""
    resp_id = resp_json.get("id", "")
    created = resp_json.get("created", 0)
    model = resp_json.get("model", "")

    def chunk(delta: Dict[str, Any], finish_reason=None, idx: int = 0) -> str:
        payload = {
            "id": resp_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {"index": idx, "delta": delta, "finish_reason": finish_reason}
            ],
        }
        return f"data: {json.dumps(payload)}\n\n"

    for choice in resp_json.get("choices", []):
        idx = choice.get("index", 0)
        msg = choice.get("message", {})
        role = msg.get("role", "assistant")
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls", []) or []
        finish = choice.get("finish_reason", "stop")

        # Initial role chunk
        yield chunk({"role": role}, idx=idx)

        # Content chunk
        if content:
            yield chunk({"content": content}, idx=idx)

        # Tool call chunks
        for i, tc in enumerate(tool_calls):
            fn = tc.get("function", {})
            yield chunk(
                {
                    "tool_calls": [
                        {
                            "index": i,
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": fn.get("name", ""),
                                "arguments": fn.get("arguments", ""),
                            },
                        }
                    ]
                },
                idx=idx,
            )

        # Finish chunk
        yield chunk({}, finish_reason=finish, idx=idx)

    yield "data: [DONE]\n\n"