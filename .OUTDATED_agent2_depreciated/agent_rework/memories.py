from collections.abc import Callable
from typing import List, Tuple, Any

from agent2.agent_rework.memory import Memory
from agent2.agent_rework.event import Event

class Memories:
    """
    Container that owns an ordered list of ``Memory`` instances and orchestrates
    their key generation and token-budget-aware decay.

    Attributes:
        memories : List[Memory]
            Ordered collection of Memory objects managed by the agent.
        _event_idx : int
            Stateful cursor for event decay.
            
    Notes
    -----
    • The class treats memories and reference events seperately when
      computing token totals and decaying (memories first, events second)
    • The event-decay cursor (`_event_idx`) is stateful so that successive
      calls continue cycling from where the previous invocation left off.
    """

    def __init__(self, memories: List[Memory]) -> None:
        """
        Parameters
        ----------
        memories : List[Memory]
            Ordered collection of Memory objects managed by the agent.
        """
        self._memories: List[Memory] = memories
        self._event_idx: int = 0

    def gen_keys(self) -> List[Tuple[str, str]]:
        """
        Collect the full `(key, value)` pairs produced by every memory.

        Returns
        -------
        List[Tuple[str, str]]
            Each tuple is exactly what ``Memory.generate`` produces.
        """
        return [mem.generate() for mem in self._memories]

    def decay(
        self,
        target_token_count: int,
        token_counter: Callable[[str], int],
        reference_events: List[Event] | None = None,
        num_events_decay: int = 1,
    ) -> bool:
        """
        Shrink memories (then events) until `target_token_count` is met
        or nothing else can be removed.

        Returns
        -------
        bool
            True  – Memories were reduced, or reduction was not necessary.
            False – Memories could not be reduced to below the target token count.
        """
        # Compute token count
        total_tokens = sum(
            token_counter(text) for _, text in (m.generate() for m in self._memories)
        )
        if reference_events:
            total_tokens += sum(
                token_counter(ev.display_content[0]) for ev in reference_events
            )

        # Main decay loop
        while total_tokens > target_token_count:
            decayed_this_round = False

            for mem in self._memories:
                if total_tokens <= target_token_count:
                    return True

                before = token_counter(mem.generate()[1])
                if mem.decay():
                    after = token_counter(mem.generate()[1])
                    total_tokens -= before - after
                    decayed_this_round = True

            if reference_events:
                for _ in range(num_events_decay):
                    if total_tokens <= target_token_count:
                        return True
                    if not reference_events:
                        break

                    if self._event_idx >= len(reference_events):
                        self._event_idx = 0
                    event = reference_events[self._event_idx]

                    before = token_counter(event.display_content[0])
                    removed = event.decay()
                    if removed:
                        after = token_counter(event.display_content[0])
                        total_tokens -= before - after
                        decayed_this_round = True
                    self._event_idx += 1

            if not decayed_this_round:
                return False

        return True
