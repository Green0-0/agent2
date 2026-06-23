import time
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse

from agent2.tool_api.api_helpers.history import HistoryRecord, HistoryStore, _err_to_str
from agent2.tool_api.abc.tool_pipeline import ToolPipeline
from agent2.tool_api.tool_validator import validate

async def _read_json(request: Request) -> Tuple[Optional[Dict], Optional[JSONResponse]]:
    """Read JSON body; return (None, error_response) on failure."""
    try:
        body = await request.json()
        if not isinstance(body, dict):
            return None, JSONResponse(
                {"success": False, "error": "Body must be a JSON object"},
                status_code=400,
            )
        return body, None
    except json.JSONDecodeError as e:
        return None, JSONResponse(
            {"success": False, "error": f"Invalid JSON: {e}"}, status_code=400
        )

def _record(
    history: HistoryStore,
    endpoint: str,
    action: str,
    request_data: Any,
    parsed_data: Any,
    response_data: Any,
    extracted_response: Any,
    errors: List[str],
    start_time: float,
    success: bool,
) -> None:
    history.add(
        HistoryRecord(
            endpoint=endpoint,
            action=action,
            request_data=request_data,
            parsed_data=parsed_data,
            response_data=response_data,
            extracted_response=extracted_response,
            errors=errors,
            latency_ms=(time.time() - start_time) * 1000.0,
            success=success,
        )
    )

async def handle_convert(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    try:
        converted = pipeline.convert_openai(body)
        _record(
            history, "custom", "convert",
            request_data=body, parsed_data=converted,
            response_data=None, extracted_response=None,
            errors=[], start_time=start_time, success=True,
        )
        return JSONResponse({"success": True, "data": converted})
    except Exception as e:
        _record(
            history, "custom", "convert",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_extract(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    response_str = body.get("response_str", "")
    schemas = body.get("schemas")
    try:
        message, raw_errors = pipeline.extract_response(response_str, schemas)
        errors = [_err_to_str(e) for e in raw_errors]
        _record(
            history, "custom", "extract",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=message,
            errors=errors, start_time=start_time, success=len(errors) == 0,
        )
        return JSONResponse(
            {"success": True, "data": {"message": message, "errors": errors}}
        )
    except Exception as e:
        _record(
            history, "custom", "extract",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_build_schema(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    tools = body.get("tools", [])
    try:
        schema_str = pipeline._get_schema_string(tools)
        _record(
            history, "custom", "build_schema",
            request_data=body, parsed_data=schema_str,
            response_data=None, extracted_response=None,
            errors=[], start_time=start_time, success=True,
        )
        return JSONResponse(
            {"success": True, "data": {"schema_string": schema_str}}
        )
    except Exception as e:
        _record(
            history, "custom", "build_schema",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_build_call(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    tool_calls = body.get("tool_calls", [])
    try:
        call_str = pipeline.tool_call_builder.build(tool_calls)
        _record(
            history, "custom", "build_call",
            request_data=body, parsed_data=call_str,
            response_data=None, extracted_response=None,
            errors=[], start_time=start_time, success=True,
        )
        return JSONResponse(
            {"success": True, "data": {"tool_call_string": call_str}}
        )
    except Exception as e:
        _record(
            history, "custom", "build_call",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_build_response(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    tool_responses = body.get("tool_responses", [])
    try:
        resp_str = pipeline.tool_response_builder.build(tool_responses)
        _record(
            history, "custom", "build_response",
            request_data=body, parsed_data=resp_str,
            response_data=None, extracted_response=None,
            errors=[], start_time=start_time, success=True,
        )
        return JSONResponse(
            {"success": True, "data": {"tool_response_string": resp_str}}
        )
    except Exception as e:
        _record(
            history, "custom", "build_response",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_validate(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    tool_call = body.get("tool_call")
    schemas = body.get("schemas", [])
    if not tool_call:
        _record(
            history, "custom", "validate",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=["tool_call required"], start_time=start_time, success=False,
        )
        return JSONResponse(
            {"success": False, "error": "tool_call required"}, status_code=400
        )
    try:
        errors = validate(tool_call, schemas)
        _record(
            history, "custom", "validate",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=errors, start_time=start_time,
            success=len(errors) == 0,
        )
        return JSONResponse(
            {"success": True, "data": {"errors": errors, "valid": len(errors) == 0}}
        )
    except Exception as e:
        _record(
            history, "custom", "validate",
            request_data=body, parsed_data=None,
            response_data=None, extracted_response=None,
            errors=[str(e)], start_time=start_time, success=False,
        )
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

async def handle_parse_roundtrip(
    request: Request, pipeline: ToolPipeline, history: HistoryStore
) -> JSONResponse:
    body, err = await _read_json(request)
    if err:
        return err
    start_time = time.time()
    errors: List[str] = []
    converted_request = None
    extracted_message = None
    try:
        chat_req = {"messages": body.get("messages", [])}
        if "tools" in body:
            chat_req["tools"] = body["tools"]
        if "tool_choice" in body:
            chat_req["tool_choice"] = body["tool_choice"]
        converted_request = pipeline.convert_openai(chat_req)
    except Exception as e:
        errors.append(f"convert: {e}")
    try:
        msg, raw_errs = pipeline.extract_response(
            body.get("response_str", ""), body.get("tools")
        )
        extracted_message = msg
        errors.extend(_err_to_str(e) for e in raw_errs)
    except Exception as e:
        errors.append(f"extract: {e}")
    _record(
        history, "custom", "roundtrip",
        request_data=body, parsed_data=converted_request,
        response_data=None, extracted_response=extracted_message,
        errors=errors, start_time=start_time, success=len(errors) == 0,
    )
    return JSONResponse(
        {
            "success": True,
            "data": {
                "converted_request": converted_request,
                "extracted_message": extracted_message,
                "errors": errors,
            },
        }
    )