"""SearchableTextArea: TextArea subclass with multi-match and change highlighting."""

from __future__ import annotations

from rich.style import Style
from textual.strip import Strip
from textual.widgets import TextArea
from textual.widgets.text_area import Selection


class SearchableTextArea(TextArea):
    """TextArea subclass that highlights ALL search matches and change markers.

    Search highlights: all matches highlighted simultaneously,
    current match in a different/brighter color.

    Change highlights: added lines get green background tint,
    modified lines get yellow/goldenrod background tint. Applied
    UNDER search highlights so search always wins visually.
    """

    _MATCH_STYLE: Style = Style(bgcolor="grey30")
    _CURRENT_MATCH_STYLE: Style = Style(bgcolor="yellow", color="black")
    _ADDED_LINE_STYLE: Style = Style(bgcolor="dark_green")
    _MODIFIED_LINE_STYLE: Style = Style(bgcolor="dark_goldenrod")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._match_positions: list[tuple[int, int]] = []
        self._match_query_len: int = 0
        self._current_match_index: int = -1
        # Change highlight state
        self._added_lines: set[int] = set()
        self._modified_lines: set[int] = set()
        self._change_highlights_active: bool = False

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

    # ----- Change highlight methods -----

    def set_change_highlights(
        self, added: list[int], modified: list[int]
    ) -> None:
        """Set change highlight line sets and trigger re-render.

        Args:
            added: 0-indexed line numbers of added lines (green tint).
            modified: 0-indexed line numbers of modified lines (yellow tint).
        """
        self._added_lines = set(added)
        self._modified_lines = set(modified)
        self._change_highlights_active = True
        self._line_cache.clear()
        self.refresh()

    def clear_change_highlights(self) -> None:
        """Clear all change highlights."""
        self._added_lines = set()
        self._modified_lines = set()
        self._change_highlights_active = False
        self._line_cache.clear()
        self.refresh()

    # ----- Rendering -----

    def render_line(self, y: int) -> Strip:
        """Render a line with change and search highlighting applied.

        Layering order:
        1. Base TextArea rendering (syntax highlighting)
        2. Change highlights (full-line background tint) -- UNDER search
        3. Search highlights (character-range, brighter) -- ON TOP
        """
        # Step 1: Get base strip from TextArea (syntax highlighting only)
        strip = TextArea.render_line(self, y)

        scroll_x, scroll_y = self.scroll_offset
        doc_row = scroll_y + y

        # Step 2: Apply change highlight (full-line background tint)
        if self._change_highlights_active:
            if doc_row in self._added_lines:
                strip = self._apply_style_to_range(
                    strip, 0, strip.cell_length, self._ADDED_LINE_STYLE
                )
            elif doc_row in self._modified_lines:
                strip = self._apply_style_to_range(
                    strip, 0, strip.cell_length, self._MODIFIED_LINE_STYLE
                )

        # Step 3: Apply search highlights (character-range, on top)
        strip = self._apply_search_highlights(strip, doc_row, scroll_x)

        return strip

    def _apply_search_highlights(
        self, strip: Strip, doc_row: int, scroll_x: int
    ) -> Strip:
        """Apply search match highlighting to a strip for a given document row."""
        if not self._match_positions or self._match_query_len == 0:
            return strip

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
            strip = self._apply_style_to_range(
                strip, visual_start, visual_end, style
            )

        return strip

    @staticmethod
    def _apply_style_to_range(
        strip: Strip, start: int, end: int, style: Style
    ) -> Strip:
        """Apply a Rich Style to a range of cells within a Strip.

        Crops the strip into three segments (before, match, after),
        replaces the style on each segment in the match range, and rejoins.
        Uses style combination with higher priority for our highlight style
        so it overrides the existing bgcolor from the theme.
        """
        from rich.segment import Segment

        total_width = strip.cell_length
        if start >= end or start >= total_width:
            return strip

        # Split into: [0..start], [start..end], [end..total]
        before = strip.crop(0, start)
        match_crop = strip.crop(start, end)
        after = strip.crop(end, total_width)

        # Replace style on each segment in the match range —
        # apply_style doesn't override existing bgcolor, so we
        # must explicitly merge with our style taking priority.
        new_segments = []
        for seg in match_crop:
            merged = seg.style + style if seg.style else style
            new_segments.append(Segment(seg.text, merged))
        match_segment = Strip(new_segments, match_crop.cell_length)

        return Strip.join([before, match_segment, after])
