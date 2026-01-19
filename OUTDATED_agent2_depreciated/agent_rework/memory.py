from abc import ABC, abstractmethod
from typing import Tuple, Any


class Memory(ABC):
    """
    Abstract base-class that represents a block of information that is fed to the agent, which may or may not be updated over time and also truncated.

    Each concrete subclass is responsible for
    1. producing a key–value representation of its current state (`generate`)
       which is used to replace filler keys in the prompt text,
    2. performing `decay` to shrink its textual footprint when token
       budgets become tight.
    """

    @abstractmethod
    def generate(self) -> Tuple[str, str]:
        """
        Return a 2-tuple `(key, text)` representing a piece of information that replaces filler keys in the prompt text.

        Returns
        -------
        Tuple[str, str]
            key   : The key to replace in the prompt.
            text  : String inserted into the LLM
                    message list.
        """

    @abstractmethod
    def decay(self) -> bool:
        """
        Reduce the textual size of this memory (if possible) and true (when text was removed) or false (if no truncation was possible).
        Warning: Getting this implementation wrong may result in infinite loops with the memories class when decay stops becoming possible.

        Returns
        -------
        bool
            True if truncation occured, false otherwise.
        """
