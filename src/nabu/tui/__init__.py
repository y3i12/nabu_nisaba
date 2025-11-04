"""
TUI subsystem: Interactive tree views for Claude.

Provides structural view with lazy loading and stateful navigation.
"""
from nabu.tui.viewable_frame import ViewableFrame, hydrate_frame_from_kuzu
from nabu.tui.frame_cache import FrameCache
from nabu.tui.structural_view_tui import StructuralViewTUI

__all__ = ['ViewableFrame', 'hydrate_frame_from_kuzu', 'FrameCache', 'StructuralViewTUI']
