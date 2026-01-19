from agent2.llm.chat import Chat
from agent2.agent.tool_formatter import ToolFormatter
from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.agent.agent_state import AgentState
from agent2.agent.tool import Tool
from agent2.file import File
from typing import List

from agent2.agent.tool_formatter import CodeACTToolFormatter
from agent2.utils.utils import get_first_import_block
from agent2.agent.smolagents.local_python_executor import LocalPythonInterpreter
import functools
import ast

class AgentResponse():
    def __init__(self, openai_completion: str, error: str = None, dangerous: str = None, done: str = None, tool_response_debug_text: str = None):
        self.openai_completion = openai_completion
        self.error = error
        self.dangerous = dangerous
        self.done = done
        self.tool_response_debug_text = tool_response_debug_text

class Agent():
    system_prompt = None
    init_message = None

    tool_response_wrapper = None

    tool_not_found_error_wrapper = None
    tool_wrong_arguments_error_wrapper = None
    tool_miscellaneous_error_wrapper = None

    tools_list = None
    tools_settings = None

    tool_formatter = None

    cached_state = None
    
    frozen = False

    bound_tool = None

    get_import_block_saved = False

    finish_tools = []

    decay_clock = 0
    decay_speed = 0

    def __init__(self, system_prompt: str, init_message: str, tools_list: List[Tool], tool_formatter: ToolFormatter, tools_settings: ToolSettings, tool_response_wrapper: str, tool_not_found_error_wrapper: str, tool_wrong_arguments_error_wrapper: str, tool_miscellaneous_error_wrapper: str, decay_speed: int):
        """
        All messages:
            * {{tools_list}} - String formatted list of avaliable tools
            * {{elements_saved_text}} - String formatted list of elements in the saved cache (must be overriden)
            * {{tools_list_name}} - Tools list, but only names
            * {{tools_examples}} - String formatted list of tool examples
            * {{tools_start}} - Starting token used for tool call blocks
            * {{tools_end}} - End token used for tool call blocks
            * {{filetype_summary}} - Summary of file types
            * {{top_level_files_list}} - Newline seperated list of top level files
            * (TBA) {{all_folders_list}} - Newline seperated list of all folder paths
            * (TBA) {{all_folders_list_spaced}} - Newline seperated list of folders, with - to seperate parents and children
            * (TBA) {{all_files_list}} - Newline seperated list of all file paths
            * (TBA) {{all_files_list_spaced}} - Newline seperated list of files, with - to seperate parents and children
        Init message:
            * {{task}} - The task to solve
        Tool response wrapper:
            * {{tool_name}} - The name of the tool attempted to be called
            * {{tool_response}} - The response from the tool
        Tool not found error:
            * {{tool_name}} - The name of the tool attempted to be called
            * {{closest_match}} - The closest match to the tool name, if any
        Tool wrong arguments error:
            * {{tool_name}} - The name of the tool attempted to be called
            * {{wrong_arguments}} - String formatted list of wrong arguments
            * {{missing_args}} - String formatted list of missing arguments
            * {{unrecognized_args}} - String formatted list of unrecognized arguments
        Tool miscellaneous error:
            * {{tool_name}} - The name of the tool attempted to be called
            * {{error_message}} - The error message
        """
        self.system_prompt = system_prompt
        self.init_message = init_message
        self.tools_list = tools_list
        self.tools_settings = tools_settings
        self.tool_formatter = tool_formatter
        self.cached_state = None

        self.get_import_block_saved = False

        self.frozen = False

        self.tool_response_wrapper = tool_response_wrapper
        self.tool_not_found_error_wrapper = tool_not_found_error_wrapper
        self.tool_wrong_arguments_error_wrapper = tool_wrong_arguments_error_wrapper
        self.tool_miscellaneous_error_wrapper = tool_miscellaneous_error_wrapper

        self.finish_tools = []

        self.decay_clock = 0
        self.decay_speed = decay_speed
        pass

    def perform_substitutions(self, message: str, task:str = None, tool_name:str = None, closest_match:str = None, wrong_arguments:str = None, missing_args:str = None, unrecognized_args:str = None, error_message:str = None, tool_response:str = None):
        elements_text = []
        import_blocks_saved_for_files = []
        self.cached_state.saved_elements.sort(key=lambda x: x[1].identifier)
        for file, element in self.cached_state.saved_elements:
            elements_text += [file.path + ":" + element.identifier]
            elements_text += ["```python"]
            if self.get_import_block_saved:
                if file not in import_blocks_saved_for_files:
                    elements_text += [get_first_import_block(file.original_content)]
                    import_blocks_saved_for_files += [file]
            elements_text += [element.to_string(number_lines = False)]
            elements_text += ["```"]
        elements_text = "\n".join(elements_text)
        
        tools_list_str = []
        for tool in self.tools_list:
            tools_list_str += [self.tool_formatter.tool_to_string(tool)]
        tools_list_str = "\n\n".join(tools_list_str)

        tools_list_name_str = []
        for tool in self.tools_list:
            tools_list_name_str += [tool.name]
        tools_list_name_str = ", ".join(tools_list_name_str)

        tools_examples_str = []
        for tool in self.tools_list:
            tools_examples_str += [tool.example_task + "\n" + self.tool_formatter.tool_start + "\n" + self.tool_formatter.json_to_string(tool.example_tool_call) + "\n" + self.tool_formatter.tool_end]
        tools_examples_str = "\n\n".join(tools_examples_str)

        tools_start = self.tool_formatter.tool_start
        tools_end = self.tool_formatter.tool_end

        filetype_summary = self.get_filetype_summary(self.cached_state.workspace)
        top_level_files_list = self.get_folder_list(self.cached_state.workspace)

        message = message.replace("{{tools_list}}", tools_list_str)
        message = message.replace("{{tools_examples}}", tools_examples_str)
        message = message.replace("{{tools_start}}", tools_start)
        message = message.replace("{{tools_end}}", tools_end)
        message = message.replace("{{filetype_summary}}", filetype_summary)
        message = message.replace("{{top_level_files_list}}", top_level_files_list)
        message = message.replace("{{tools_list_name}}", tools_list_name_str)
        message = message.replace("{{elements_saved_text}}", elements_text)
        if task is not None:
            message = message.replace("{{task}}", task)
        if tool_name is not None:
            message = message.replace("{{tool_name}}", tool_name)
        if closest_match is not None:
            message = message.replace("{{closest_match}}", closest_match)
        else:
            message = message.replace("{{closest_match}}", f"<None found>")
        if wrong_arguments is not None:
            message = message.replace("{{wrong_arguments}}", wrong_arguments)
        if missing_args is not None:
            message = message.replace("{{missing_args}}", missing_args)
        if unrecognized_args is not None:
            message = message.replace("{{unrecognized_args}}", unrecognized_args)
        if error_message is not None:
            message = message.replace("{{error_message}}", error_message)
        if tool_response is not None:
            message = message.replace("{{tool_response}}", tool_response)
        return message

    def start(self, task: str, files: List[File] = [], copy_saved_elements = None):
        self.decay_clock = 0
        self.cached_state = AgentState(None, files)
        if copy_saved_elements is not None:
            self.cached_state.saved_elements = copy_saved_elements 
        system_prompt_final = self.perform_substitutions(self.system_prompt)
        final_init_message = self.perform_substitutions(self.init_message, task)
        self.cached_state.chat = Chat(system_prompt_final, final_init_message)
        self.bound_tool = None
        print("==== SYSTEM PROMPT: ====")
        print(system_prompt_final)
        print("==== INIT MESSAGE: ====")
        print(final_init_message)
        self.frozen = False
        return AgentResponse(self.cached_state.chat.toOAI(), None, None, None)
    
    def step(self, response_str : str):
        if self.frozen:
            return None
        self.decay_clock += self.decay_speed
        while self.decay_clock >= 1:
            self.decay_clock -= 1
            self.cached_state.chat.decay()
        response_trimmed = response_str.split(self.tool_formatter.tool_end)[0]
        response_parts = response_trimmed.split(self.tool_formatter.tool_start)
        if self.bound_tool is not None:
            try:
                print("==== RESPONSE WHILE BOUND TOOL: ====")
                print(response_parts[0])
                tool_response = self.bound_tool(response_parts[0])
                response_str = self.perform_substitutions(self.tool_response_wrapper, tool_response=tool_response[0], tool_name=self.bound_tool.func.__name__)
                print("==== TOOL RESPONSE: ====")
                print(tool_response[0])
                self.cached_state.chat.append(response_str)
                self.bound_tool = tool_response[1]
                return AgentResponse(self.cached_state.chat.toOAI(), None, None, None, response_str)
            except Exception as e:
                error_msg = self.perform_substitutions(self.tool_miscellaneous_error_wrapper, tool_name=self.bound_tool.func.__name__, error_message=str(e))
                self.cached_state.chat.append(error_msg)
                self.bound_tool = None
                print("==== ERROR: ====")
                print(error_msg)
                return AgentResponse(self.cached_state.chat.toOAI(), f"Miscellaneous error: {str(e)}", None, None, error_msg)
        if "```" in response_parts[0]:
            code_block_segments = response_parts[0].split("```")
            last_section = code_block_segments[-2]
            # Remove excess newline at the start
            last_section = last_section[last_section.find("\n"):].strip()
            self.cached_state.last_code_block = last_section
            print("==== CACHED CODE BLOCK ====")
        if len(response_parts) == 1:
            # Finished
            print("==== FINISHED: ====")
            print(response_parts[0].strip())
            self.cached_state.chat.append(response_parts[0].strip())
            origresponse = AgentResponse(self.cached_state.chat.toOAI(), None, None, response_parts[0].strip())
            for finish_tool in self.finish_tools:
                finish_tool(origresponse, self.cached_state)
            return origresponse
        response_parts[1] = response_parts[1].strip()
        self.cached_state.chat.append(response_trimmed + self.tool_formatter.tool_end)
        print("==== RESPONSE: ====")
        print(response_trimmed + self.tool_formatter.tool_end)
        #########
        # CodeAct agents unfortunately need to be manually overriden as they do something completely different
        if isinstance(self.tool_formatter, CodeACTToolFormatter):
            try:
                tool_call = self.tool_formatter.string_to_json(response_parts[1])
                executable_tools = {}
                for tool in self.tools_list:
                    # Create the partial tool with fixed arguments
                    partial_tool = functools.partial(tool, self.cached_state, self.tools_settings)
                    
                    # Define a wrapper to update self.bound_tool and return the first element
                    def wrapped_tool(*args, _pt=partial_tool, **kwargs):
                        result = _pt(*args, **kwargs)  # Call the partial tool
                        self.bound_tool = result[1]    # Set the 4th element (index 3)
                        return result[0]               # Return the first element (index 0)
                    
                    # Add the wrapped tool to executable_tools
                    executable_tools[tool.name] = wrapped_tool
                pythonInterpreter = LocalPythonInterpreter([], executable_tools)
                execution_result = pythonInterpreter(tool_call, {})[0]
                print("==== TOOL RESPONSE ====")
                print(execution_result)
                self.cached_state.chat.append(execution_result)
                return AgentResponse(self.cached_state.chat.toOAI(), None, None, None, execution_result)
            except Exception as e:
                error_output = str(e)
                if "def" in tool_call or "class" in tool_call:
                    error_output += "\nPlease do not use tool call code blocks for anything besides using tools, and do not use tools you don't have access to."
                self.cached_state.chat.append(error_output)
                print("==== ERROR ====")
                print(error_output)
                return AgentResponse(self.cached_state.chat.toOAI(), f"Code block error: {str(e)}", None, None, error_output)
        #########
        # Attempt to parse the tool call
        try:
            tool_call = None
            tool_name = "Unknown"
            tool_call = self.tool_formatter.string_to_json(response_parts[1])
            tool_name = tool_call["name"]
            # Attempt to execute the tool call
            matched_tool = next((t for t in self.tools_list if t.name == tool_call["name"]), None)
            if matched_tool is None:
                # Tool not found
                # split by spaces and underscores
                lookup_keys = tool_call["name"].split(" ") + tool_call["name"].split("_")
                # Make lookup keys lower
                lookup_keys = [k.lower() for k in lookup_keys]
                closest_tool = next((t for t in self.tools_list if any(k in t.name.lower() for k in lookup_keys)), None)
                if closest_tool is None:
                    # Search even more deeply into descriptions
                    closest_tool = next((t for t in self.tools_list if any(k in t.description.lower() or k in t.example_task.lower() or k in str(t.required_args).lower() or k in str(t.optional_args).lower() for k in lookup_keys)), None)
                if closest_tool is None:
                    error_msg = self.perform_substitutions(self.tool_not_found_error_wrapper, tool_name=tool_call["name"])
                else:
                    error_msg = self.perform_substitutions(self.tool_not_found_error_wrapper, tool_name=tool_call["name"], closest_match=closest_tool.name)
                print("==== ERROR: ====")
                print(error_msg)
                self.cached_state.chat.append(error_msg)
                return AgentResponse(self.cached_state.chat.toOAI(), f"Failed to find tool: {tool_call['name']}", None, None, error_msg)
            print("==== TOOL CALL ARGS: ====")
            print(tool_call["arguments"])
            args_errors = matched_tool.match(tool_call)
            if args_errors is not None:
                # Wrong arguments
                print(args_errors)
                error_msg = self.perform_substitutions(self.tool_wrong_arguments_error_wrapper, tool_name=tool_call["name"], wrong_arguments = ", ".join(args_errors[2]), missing_args=", ".join(args_errors[0]), unrecognized_args=", ".join(args_errors[1]))
                self.cached_state.chat.append(error_msg)
                print("==== ERROR: ====")
                print(error_msg)
                return AgentResponse(self.cached_state.chat.toOAI(), f"Arguments didnt match tool: {tool_call['name']}", None, None, error_msg)
            tool_response = matched_tool(self.cached_state, self.tools_settings, **tool_call["arguments"])
            print("==== TOOL RESPONSE: ====")
            print(tool_response[0])
            response_true = self.perform_substitutions(self.tool_response_wrapper, tool_name=tool_call["name"], tool_response=tool_response[0])
            self.cached_state.chat.append(response_true)
            self.bound_tool = tool_response[1]
            return AgentResponse(self.cached_state.chat.toOAI(), None, None, None, response_true)
        except Exception as e:
            error_msg = self.perform_substitutions(self.tool_miscellaneous_error_wrapper, tool_name=tool_name, error_message=str(e))
            self.cached_state.chat.append(error_msg)
            print("==== ERROR: ====")
            print(error_msg)
            return AgentResponse(self.cached_state.chat.toOAI(), f"Miscellaneous error: {str(e)}", None, None, error_msg)

    
    def get_folder_list(self, files: List[File]) -> str:
        """
        Get formatted string of root-level folders from files
        
        Returns:
            String with one root folder path per line, sorted alphabetically
        """
        folders = set()
        for file in files:
            path = file.path
            if path.startswith('.'):
                continue
            # Split path and get first directory only
            if "/" in path:
                parts = path.split('/')
                if len(parts) > 1:
                    folder = parts[0] + '/'
                    folders.add(folder)
            else:
                parts = path.split('\\')
                if len(parts) > 1:
                    folder = parts[0] + '/'
                    folders.add(folder)
        
        return '\n'.join(sorted(folders))

    def get_filetype_summary(self, files: List[File]) -> str:
        """
        Get formatted string of file type percentages
        
        Returns:
            String showing percentage breakdown of file extensions
        """
        ext_counts = {}
        total = 0
        
        # Count extensions
        for file in files:
            ext_counts[file.extension] = ext_counts.get(file.extension, 0) + 1
            total += 1
        
        # Calculate percentages
        summary = []
        for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
            percent = round((count / total) * 100)
            if percent < 10:
                continue
            if ext == 'Unknown':
                summary.append(f"{ext}: {percent}%")
            else:
                summary.append(f"{ext.capitalize()} (.{ext}): {percent}%")
        
        return '\n'.join(summary)
