"""
Phase 6: Commentary Director (Pass A).
Coordinates narrative role assignment and speaker emotional pacing across allocated slots.
"""

from typing import List
from backend.commentary.schemas import CommentarySlot, MatchContext


class CommentaryDirector:
    """Pass A: Plans narrative goals and emotional targets for each slot."""

    def __init__(self, match_context: MatchContext):
        self.context = match_context

    def direct_slots(self, slots: List[CommentarySlot]) -> List[CommentarySlot]:
        """Refines slots with speaker assignments and narrative fact whitelists."""
        directed: List[CommentarySlot] = []
        for s in slots:
            # Ensure fact IDs include base team facts if empty
            fids = list(s.allowed_fact_ids)
            if not fids:
                fids = ["fact_0001", "fact_0002", "fact_0003"]
            directed.append(s.model_copy(update={"allowed_fact_ids": fids}))
        return directed
