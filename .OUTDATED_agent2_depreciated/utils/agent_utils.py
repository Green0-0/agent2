# utils.py
import json
from typing import Dict, Any
from agent2.agent.agent_depreciated import Agent
from agent2.agent.tool_formatter import XMLToolFormatter, JSONToolFormatter, MarkdownToolFormatter, CodeACTToolFormatter
from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.agent.tool import Tool
from agent2.tools_common.input_tools.searching import search
from agent2.tools_common.input_tools.viewing import view_element, view_element_at, view_file, view_file_raw, view_lines
from agent2.tools_common.output_tools.editing import replace_lines, replace_block, replace_element, replace_element_at, open_element, open_element_at

tools_list = [Tool(replace_lines), 
              Tool(replace_block), 
              Tool(replace_element),
              Tool(replace_element_at),
              Tool(open_element),
              Tool(open_element_at),
              Tool(view_lines), 
              Tool(view_file), 
              Tool(view_file_raw), 
              Tool(view_element), 
              Tool(view_element_at),
              Tool(search)
              ]

def save_agent_to_json(agent: Agent, file_path: str):
    if isinstance(agent.tool_formatter, JSONToolFormatter):
        type = "JSON"
    elif isinstance(agent.tool_formatter, XMLToolFormatter):
        type = "XML"
    elif isinstance(agent.tool_formatter, MarkdownToolFormatter):
        type = "Markdown"
    elif isinstance(agent.tool_formatter, CodeACTToolFormatter):
        type = "CodeAct"
    agent.tools_settings.embeddings_model = None
    config = {
        "system_prompt": agent.system_prompt,
        "init_message": agent.init_message,
        "tool_formatter": {
            "type": type,
            "tool_start": agent.tool_formatter.tool_start,
            "tool_end": agent.tool_formatter.tool_end
        },
        "decay_speed": agent.decay_speed,
        "tool_settings": vars(agent.tools_settings),
        "selected_tools": [tool.name for tool in agent.tools_list],
        "prompt_templates": {
            "response_wrapper": agent.tool_response_wrapper,
            "not_found_error": agent.tool_not_found_error_wrapper,
            "wrong_args_error": agent.tool_wrong_arguments_error_wrapper,
            "misc_error": agent.tool_miscellaneous_error_wrapper
        }
    }
    with open(file_path, 'w') as f:
        json.dump(config, f, indent=2)

def load_agent_from_json(file_path: str) -> Agent:
    with open(file_path, 'r') as f:
        config = json.load(f)

    # Tool formatter selection
    if config['tool_formatter']['type'] == 'JSON':
        formatter = JSONToolFormatter(
            tool_start=config['tool_formatter']['tool_start'],
            tool_end=config['tool_formatter']['tool_end']
        )
    elif config['tool_formatter']['type'] == 'XML':
        formatter = XMLToolFormatter(
            tool_start=config['tool_formatter']['tool_start'],
            tool_end=config['tool_formatter']['tool_end']
        )
    elif config['tool_formatter']['type'] == 'Markdown':
        formatter = MarkdownToolFormatter(
            tool_start=config['tool_formatter']['tool_start'],
            tool_end=config['tool_formatter']['tool_end']
        )
    elif config['tool_formatter']['type'] == 'CodeAct':
        formatter = CodeACTToolFormatter(
            tool_start=config['tool_formatter']['tool_start'],
            tool_end=config['tool_formatter']['tool_end']
        )
    
    # Settings reconstruction
    settings = ToolSettings()
    for k, v in config['tool_settings'].items():
        if hasattr(settings, k):
            setattr(settings, k, v)
    if settings.embeddings_model_path == None or settings.embeddings_model_path.lower() == "none" or settings.embeddings_model_path.lower() == "false" or settings.embeddings_model_path.lower() == "":
        settings.embeddings_model_path = None
    
    # Tool selection
    selected_tools = [t for t in tools_list if t.name in config['selected_tools']]
    
    return Agent(
        system_prompt=config['system_prompt'],
        init_message=config['init_message'],
        tools_list=selected_tools,
        tool_formatter=formatter,
        tools_settings=settings,
        tool_response_wrapper=config['prompt_templates']['response_wrapper'],
        tool_not_found_error_wrapper=config['prompt_templates']['not_found_error'],
        tool_wrong_arguments_error_wrapper=config['prompt_templates']['wrong_args_error'],
        tool_miscellaneous_error_wrapper=config['prompt_templates']['misc_error'],
        decay_speed=config['decay_speed']
    )