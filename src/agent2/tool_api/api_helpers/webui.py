import json
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("TOOL_API_URL", "http://localhost:8000")

def get_current_format():
    try:
        r = requests.get(API_URL, timeout=5)
        if r.status_code == 200:
            return r.json().get("format", "xml")
    except:
        pass
    return "xml"

CURRENT_FORMAT = get_current_format()

st.set_page_config(page_title="Tool API WebUI", page_icon="🛠", layout="wide")
st.title(f"🛠 Tool API WebUI ({CURRENT_FORMAT})")

EXAMPLE_OAI_REQUEST = {
    "model": "example-model",
    "messages": [
        {
            "role": "system",
            "content": "You have access to the following tools:\n{{llm_tools_list}}",
        },
        {"role": "user", "content": "What's the weather in Tokyo?"},
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature units",
                        },
                    },
                    "required": ["city"],
                },
            },
        }
    ],
}

EXAMPLES = {
    "xml": "I'll check the weather for you.\n<tool_call>\n<name>get_weather</name>\n<city>Tokyo</city>\n<units>celsius</units>\n</tool_call>",
    "json": "I'll check the weather for you.\n```json\n[\n  {\n    \"name\": \"get_weather\",\n    \"arguments\": {\n      \"city\": \"Tokyo\",\n      \"units\": \"celsius\"\n    }\n  }\n]\n```",
    "md": "I'll check the weather for you.\n# Tool Use\n## Name: get_weather\n### city: Tokyo\n### units: celsius\n# Tool End",
    "fake_codeact": "I'll check the weather for you.\n<code>\nget_weather(city='Tokyo', units='celsius')\n</code>"
}

EXAMPLE_RESPONSE_STR = EXAMPLES.get(CURRENT_FORMAT, EXAMPLES["xml"])

def _safe_get(url: str, **kwargs):
    try:
        r = requests.get(url, timeout=10, **kwargs)
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)

def _safe_post(url: str, payload):
    try:
        r = requests.post(url, json=payload, timeout=30)
        return r.json(), r.status_code
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

def _st_write_anything(data):
    """Helper to correctly display strings vs json in Streamlit."""
    if isinstance(data, (dict, list)):
        st.json(data)
    else:
        st.code(str(data))

tab1, tab2, tab3 = st.tabs(["🧪 Testing Environment", "📜 History", "📊 Statistics"])

# ============================================================
# Tab 1: Testing Environment
# ============================================================
with tab1:
    st.header("Testing Environment")
    st.write("Paste input of various formats and convert back and forth.")

    operation = st.selectbox(
        "Operation",
        [
            "convert_request",
            "extract_response",
            "build_schema",
            "build_call",
            "build_response",
            "validate",
            "roundtrip",
        ],
        format_func=lambda x: {
            "convert_request": "Convert OAI chat (with tools) → without tools",
            "extract_response": "Extract tool calls from a response string",
            "build_schema": "Build schema string from tool schemas",
            "build_call": "Build tool-call string from JSON",
            "build_response": "Build tool-response string from JSON",
            "validate": "Validate a tool call against schemas",
            "roundtrip": "Round-trip: convert request + extract response",
        }[x],
    )

    col_load, col_blank = st.columns([1, 3])
    with col_load:
        if st.button("Load Example (OAI request)"):
            st.session_state["input_text"] = json.dumps(EXAMPLE_OAI_REQUEST, indent=2)
        if st.button("Load Example (response string)"):
            st.session_state["input_text"] = json.dumps(
                {"response_str": EXAMPLE_RESPONSE_STR}, indent=2
            )

    input_text = st.text_area(
        "Input (JSON)", height=300, key="input_text",
        placeholder='{"response_str": "...", "schemas": [...]}  or  {"tools": [...], "messages": [...]}',
    )

    if st.button("Run", type="primary"):
        if not input_text.strip():
            st.warning("Please provide input.")
        else:
            try:
                payload = json.loads(input_text)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
                payload = None

            if payload is not None:
                url = f"{API_URL}/custom/{operation}"
                result, status = _safe_post(url, payload)
                if status == 200 and result.get("success"):
                    st.success("✅ Success")
                    _st_write_anything(result.get("data", {}))
                else:
                    st.error(
                        f"❌ Failed (HTTP {status}): "
                        f"{result.get('error') if isinstance(result, dict) else result}"
                    )

    st.divider()
    st.subheader("Quick reference - expected input shapes")
    with st.expander("Show input shapes"):
        st.code(
            "convert_request:  { 'messages':[...], 'tools':[...] }\n"
            "extract_response: { 'response_str':'...', 'schemas':[...] }\n"
            "build_schema:     { 'tools':[<OpenAI tool def>, ...] }\n"
            "build_call:       { 'tool_calls':[<OpenAI tool call>, ...] }\n"
            "build_response:   { 'tool_responses':[{'role':'tool','content':'...'}, ...] }\n"
            "validate:         { 'tool_call':<OpenAI tool call>, 'schemas':[...] }\n"
            "roundtrip:        { 'messages':[...], 'tools':[...], 'response_str':'...' }",
            language="text",
        )

# ============================================================
# Tab 2: History
# ============================================================
with tab2:
    st.header("Request History")
    refresh = st.button("🔄 Refresh")

    col_oai, col_custom = st.columns(2)

    # ---- OpenAI history ----
    with col_oai:
        st.subheader("OpenAI Endpoint")
        records, err = _safe_get(f"{API_URL}/custom/history", params={"endpoint": "openai", "limit": 50})
        if err:
            st.error(f"Fetch failed: {err}")
        elif not records:
            st.info("No OpenAI requests recorded yet.")
        else:
            for r in records:
                ts = datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
                icon = "✅" if r["success"] else "❌"
                label = f"{ts}  {icon}  {r['latency_ms']:.1f}ms"
                if r.get("errors"):
                    label += f"  errors={len(r['errors'])}"
                with st.expander(label):
                    if r.get("errors"):
                        st.error(f"Errors: {r['errors']}")
                    req = r.get("request_data") or {}
                    if isinstance(req, dict) and "messages" in req:
                        st.caption(f"Model: {req.get('model','?')}  "
                                   f"Msgs: {len(req.get('messages',[]))}  "
                                   f"Tools: {len(req.get('tools',[]))}")
                    st.write("**Original Request:**")
                    _st_write_anything(req)
                    if r.get("parsed_data") is not None:
                        st.write("**Converted (sent to backend):**")
                        _st_write_anything(r["parsed_data"])
                    if r.get("response_data"):
                        st.write("**Backend Response:**")
                        _st_write_anything(r["response_data"])
                    if r.get("extracted_response") is not None:
                        st.write("**Extracted (returned to client):**")
                        _st_write_anything(r["extracted_response"])

    # ---- Custom history ----
    with col_custom:
        st.subheader("Custom Endpoint")
        records, err = _safe_get(f"{API_URL}/custom/history", params={"endpoint": "custom", "limit": 50})
        if err:
            st.error(f"Fetch failed: {err}")
        elif not records:
            st.info("No custom-endpoint requests recorded yet.")
        else:
            for r in records:
                ts = datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
                icon = "✅" if r["success"] else "❌"
                # Action is now correctly retrieved from the history record root
                action = r.get("action", "?")
                label = f"{ts}  {icon}  [{action}]  {r['latency_ms']:.1f}ms"
                with st.expander(label):
                    if r.get("errors"):
                        st.error(f"Errors: {r['errors']}")
                    st.write("**Input:**")
                    _st_write_anything(r.get("request_data") or {})
                    if r.get("parsed_data") is not None:
                        st.write("**Output:**")
                        _st_write_anything(r["parsed_data"])
                    if r.get("extracted_response") is not None:
                        st.write("**Extracted:**")
                        _st_write_anything(r["extracted_response"])

    if refresh:
        st.rerun()

# ============================================================
# Tab 3: Statistics
# ============================================================
with tab3:
    st.header("Runtime Statistics")
    refresh2 = st.button("🔄 Refresh", key="stats_refresh")

    def _render_stats_block(endpoint_name: str, endpoint_key: str):
        st.subheader(f"{endpoint_name} Endpoint")
        stats, err = _safe_get(f"{API_URL}/custom/stats", params={"endpoint": endpoint_key})
        if err:
            st.error(f"Fetch failed: {err}")
            return
        if not stats:
            st.info("No data.")
            return

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Requests", stats.get("total_requests", 0))
        c2.metric("Successful", stats.get("successful_requests", 0))
        c3.metric("Failed", stats.get("failed_requests", 0))
        c4.metric("Success Rate", f"{stats.get('success_rate', 0) * 100:.1f}%")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Total Tool Calls", stats.get("total_tool_calls", 0))
        c6.metric("Avg Latency (ms)", f"{stats.get('latency_avg_ms', 0):.1f}")
        c7.metric("Min Latency (ms)", f"{stats.get('latency_min_ms', 0):.1f}")
        c8.metric("Max Latency (ms)", f"{stats.get('latency_max_ms', 0):.1f}")

        if endpoint_key == "openai":
            cw1, cw2 = st.columns(2)
            cw1.metric("Requests w/ Tools", stats.get("requests_with_tools", 0))
            cw2.metric("Requests w/o Tools", stats.get("requests_without_tools", 0))

        action_counts = stats.get("action_counts", {}) or {}
        if action_counts:
            st.write("**Action counts:**")
            st.dataframe(
                pd.DataFrame(action_counts.items(), columns=["Action", "Count"]),
                use_container_width=True, hide_index=True,
            )

        tool_usage = stats.get("tool_usage", {}) or {}
        st.write("**Tool usage:**")
        if tool_usage:
            st.dataframe(
                pd.DataFrame(tool_usage.items(), columns=["Tool", "Count"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No tool calls recorded.")

        errors_by_type = stats.get("errors_by_type", {}) or {}
        st.write("**Errors by type:**")
        if errors_by_type:
            st.dataframe(
                pd.DataFrame(errors_by_type.items(), columns=["Error", "Count"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No errors recorded.")

    col_l, col_r = st.columns(2)
    with col_l:
        _render_stats_block("OpenAI", "openai")
    with col_r:
        _render_stats_block("Custom", "custom")

    if refresh2:
        st.rerun()