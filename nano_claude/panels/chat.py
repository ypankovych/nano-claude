"""Chat panel -- placeholder for Phase 3."""

from textual.widgets import Static

from nano_claude.panels.base import BasePanel


class ChatPanel(BasePanel):
    """Right panel: Claude chat interface.

    Phase 3 will replace the placeholder with a chat widget.
    """

    def compose(self):
        placeholder = Static(
            "Claude Chat\n\nPhase 3 will add chat interface here.",
            id="chat-placeholder",
        )
        placeholder.can_focus = True
        yield placeholder
