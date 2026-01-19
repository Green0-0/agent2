from typing import List
from agent2.element import Element
from agent2.file import File
import requests
import time
import os
import re

from typing import List

# Assume this function is implemented to interface with your LLM API
def get_completion(oai_messages, timeout_duration : int = 120, max_retries : int = 5, api_url : str = "https://api.mistral.ai/v1", api_key : str = os.environ.get("API_KEY"), model : str = "mistral-small-2501") -> str:  
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': f"{model}",
        'messages': oai_messages,
        'stream': False,
        'temperature': 0.3,
        'top_p': 0.95,
        'max_tokens': 2000,
        'stop': ['</s>', "<|im_end|>", "</tool_call>", "</tool_use>"]
    }
    
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.post(api_url + '/chat/completions', headers=headers, json=data, timeout=timeout_duration)
            response.raise_for_status()  # Raise an exception for bad status codes
            response = response.json()
            try: 
                response = response['choices'][0]['message']['content']
                return response
            except KeyError:
                print("Response does not have the expected format: ", response)
        except requests.Timeout:
            print(f"Request timed out, retrying ({retry_count}/{max_retries})...")
        except requests.RequestException as e:
            print(f"Error during request: {str(e)}")
            print(f"Retrying ({retry_count}/{max_retries})...")
        retry_count += 1
        time.sleep(10)
    
    raise requests.RequestException("Max retries exceeded")

def get_first_import_block(code):
    lines = code.split('\n')
    block_lines = []
    in_block = False
    open_parens = 0
    line_continuation = False

    for line in lines:
        stripped = line.strip()

        if not in_block:
            if stripped == '' or stripped.startswith('#'):
                continue
            elif 'import' in line:
                in_block = True
                block_lines.append(line)
                open_parens += line.count('(') - line.count(')')
                line_continuation = line.rstrip().endswith('\\')
        else:
            is_comment_or_empty = stripped == '' or stripped.startswith('#')
            if is_comment_or_empty:
                block_lines.append(line)
                continue

            if line_continuation or open_parens > 0:
                block_lines.append(line)
                open_parens += line.count('(') - line.count(')')
                line_continuation = line.rstrip().endswith('\\')
            else:
                if 'import' in line:
                    block_lines.append(line)
                    open_parens += line.count('(') - line.count(')')
                    line_continuation = line.rstrip().endswith('\\')
                else:
                    break

    return '\n'.join(block_lines)