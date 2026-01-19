from enum import Enum
from agent2.file import File
from agent2.element import Element

class InteractionType(Enum):
    """
    Enumeration of different types of interactions that can occur in the LLM Agent system.
    
    This enum defines the various ways an agent can interact with files and elements
    during the execution flow.
    """
    VIEW = "view"
    SEARCH = "search"
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"
    EXECUTE = "execute"

class Interaction:
    """
    Represents an interaction between the agent and a file (and its specific elements).

    Attributes:
        type: The type of interaction being performed (InteractionType enum value)
        target_file: The file that is the target of this interaction, None if no specific file is targeted
        target_element: Optional specific element within the target file (e.g., function name,
                       line number, section identifier, etc.). None if no specific element is targeted.
        interaction_details: Optional additional details or context about the interaction
    """
    
    def __init__(
        self,
        interaction_type: InteractionType,
        target_file: File = None,
        target_element: Element = None,
        interaction_details: str = None
    ) -> None:
        """
        Initialize an Interaction with the specified type, file, and optional element.
        
        Args:
            interaction_type: The type of interaction being performed (view, search, modify, create, delete, execute)
            target_file: The file that is the target of this interaction
            target_element: Optional specific element within the target file
            interaction_details: Details or context about the interaction
        
        Raises:
            TypeError: If interaction_type is not an instance of InteractionType
            ValueError: If target_element is specified without a target_file, or if required parameters
                       are missing for specific interaction types
        """
        if not isinstance(interaction_type, InteractionType):
            raise TypeError("interaction_type must be an instance of InteractionType enum")
        
        if target_element is not None and target_file is None:
            raise ValueError("target_element cannot be specified without a target_file")
        
        # Validate required parameters for specific interaction types
        if interaction_type in [InteractionType.VIEW, InteractionType.MODIFY, InteractionType.CREATE, InteractionType.DELETE]:
            if target_file is None:
                raise ValueError(f"{interaction_type.value} operation requires a target_file specification")
        
        if interaction_type in [InteractionType.SEARCH, InteractionType.EXECUTE]:
            if interaction_details is None:
                raise ValueError(f"{interaction_type.value} operation requires interaction_details")
        
        self.type: InteractionType = interaction_type
        self.target_file: File = target_file
        self.target_element: Element = target_element
        self.interaction_details: str = interaction_details
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the Interaction.
        
        Returns:
            A formatted string describing the interaction
        """
        if self.type in [InteractionType.SEARCH, InteractionType.EXECUTE]:
            return f"{self.type.value} operation: '{self.interaction_details}'"
        elif self.target_element is not None:
            return f"{self.type.value} operation on element '{self.target_element}' in file '{self.target_file}'"
        else:
            return f"{self.type.value} operation on file '{self.target_file}'"
    
    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.
        
        Returns:
            A string showing the Interaction's internal state
        """
        return (f"Interaction(type={self.type}, "
                f"target_file={self.target_file!r}, "
                f"target_element={self.target_element!r}, "
                f"interaction_details={self.interaction_details!r})")
