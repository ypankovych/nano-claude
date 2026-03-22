"""SearchableTextArea: TextArea subclass with multi-match highlighting support."""

from __future__ import annotations

from rich.style import Style
from textual.strip import Strip
from textual.widgets import TextArea
from textual.widgets.text_area import Selection


class SearchableTextArea(TextArea):
    """TextArea subclass that highlights ALL search matches simultaneously.

    Per user decision: all matches highlighted in the file simultaneously,
    current match in a different/brighter color.

    Non-current matches: muted grey background.
    Current match: bright yellow background with black text.
    """

    _MATCH_STYLE: Style = Style(bgcolor="grey30")
    _CURRENT_MATCH_STYLE: Style = Style(bgcolor="yellow", color="black")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._match_positions: list[tuple[int, int]] = []
        self._match_query_len: int = 0
        self._current_match_index: int = -1

    def set_search_matches(
        self, matches: list[tuple[int, int]], query_len: int
    ) -> None:
        """Store match positions and trigger re-render with highlights.

        Args:
            matches: List of (row, col) tuples for each match start.
            query_len: Length of the search query (for highlight span).
        """
        self._match_positions = matches
        self._match_query_len = query_len
        self._current_match_index = 0 if matches else -1
        self._line_cache.clear()
        self.refresh()

    def set_current_match(self, index: int) -> None:
        """Set the current (highlighted) match and scroll to it.

        Args:
            index: Index into _match_positions for the current match.
        """
        self._current_match_index = index
        if 0 <= index < len(self._match_positions):
            row, col = self._match_positions[index]
            end_col = col + self._match_query_len
            self.selection = Selection(start=(row, col), end=(row, end_col))
            self.scroll_cursor_visible()
        self._line_cache.clear()
        self.refresh()

    def clear_search_matches(self) -> None:
        """Clear all match highlights."""
        self._match_positions = []
        self._match_query_len = 0
        self._current_match_index = -1
        self._line_cache.clear()
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render a line with search match highlighting applied.

        Calls the parent render_line for default rendering, then overlays
        match highlight styles at the correct positions.
        """
        strip = super().render_line(y)

        if not self._match_positions or self._match_query_len == 0:
            return strip

        # Determine which document row this visual line y corresponds to
        scroll_x, scroll_y = self.scroll_offset
        doc_row = scroll_y + y

        # Find all matches on this document row
        row_matches = [
            (i, col)
            for i, (r, col) in enumerate(self._match_positions)
            if r == doc_row
        ]

        if not row_matches:
            return strip

        # Calculate gutter width offset (line numbers take space in the Strip)
        gutter_width = self.gutter_width if self.show_line_numbers else 0

        # Apply highlighting to each match on this line
        for match_idx, col in row_matches:
            # Choose style based on whether this is the current match
            if match_idx == self._current_match_index:
                style = self._CURRENT_MATCH_STYLE
            else:
                style = self._MATCH_STYLE

            # Convert document column to visual column (accounting for gutter and scroll)
            visual_start = gutter_width + col - scroll_x
            visual_end = visual_start + self._match_query_len

            # Clamp to strip bounds
            strip_width = strip.cell_length
            if visual_end <= 0 or visual_start >= strip_width:
                continue

            visual_start = max(0, visual_start)
            visual_end = min(strip_width, visual_end)

            # Apply style by cropping, styling, and rejoining the strip
            strip = self._apply_style_to_range(strip, visual_start, visual_end, style)

        return strip

    @staticmethod
    def _apply_style_to_range(
        strip: Strip, start: int, end: int, style: Style
    ) -> Strip:
        """Apply a Rich Style to a range of cells within a Strip.

        Crops the strip into three segments (before, match, after),
        applies the style to the match segment, and rejoins.
        """
        total_width = strip.cell_length
        if start >= end or start >= total_width:
            return strip

        # Split into: [0..start], [start..end], [end..total]
        before = strip.crop(0, start)
        match_segment = strip.crop(start, end).apply_style(style)
        after = strip.crop(end, total_width)

        return Strip.join([before, match_segment, after])
