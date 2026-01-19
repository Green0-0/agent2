from abc import ABC, abstractmethod
from typing import List, Dict

class ToolPipeline(ABC):
    """The ToolPipeline is a pipeline of tool call extractors, tool call builders, and tool schema builders."""
    
    @abstractmethod
    def convert_openai(openai_json: List[Dict]) -> List[Dict]:
        """Converts an OpenAI chat with tools to another OpenAI chat with no tools.
        
        Args:
            openai_json (List[Dict]): The OpenAI chat with tool schemas/calls to convert.
            
        Returns:
            List[Dict]: The OpenAI chat with no tools. 
        """
        pass
    
    @abstractmethod
    def extract_response(self, response_str: str) -> Dict:
        """Parses a response string into an OpenAI message dict.

        Args:
            response_str (str): The response string to parse.
            
        Returns:
            Dict: The openai message dict.
        """
        pass