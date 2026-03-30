"""Lazy matplotlib canvas that only creates FigureCanvasQTAgg on first use.

This prevents segfaults from having too many active matplotlib canvases
in a PyQt6 tab widget. The crash occurs when Qt repaints canvases on hidden
tabs during rapid tab switching.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure


class LazyCanvas(QWidget):
    """A wrapper that shows a placeholder until a matplotlib Figure is needed.

    Usage (drop-in replacement):
        # Old:
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        # New:
        self.lazy_canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        layout.addWidget(self.lazy_canvas)
        # Then when you need to plot:
        fig = self.lazy_canvas.figure  # creates canvas on first access
        self.lazy_canvas.draw()
    """

    def __init__(self, figsize=(8, 5), dpi=100, parent=None):
        super().__init__(parent)
        self._figsize = figsize
        self._dpi = dpi
        self._figure: Figure | None = None
        self._canvas = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder shown until first use
        self._placeholder = QLabel("Run a calculation to see the plot here")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #555577; font-size: 14px; font-style: italic; "
            "background-color: #1e1e2e; border: 1px dashed #333355; "
            "border-radius: 4px; padding: 40px;"
        )
        self._layout.addWidget(self._placeholder)

    @property
    def figure(self) -> Figure:
        """Get or create the matplotlib Figure (creates canvas on first access)."""
        if self._figure is None:
            self._materialize()
        return self._figure

    def _materialize(self):
        """Create the real Figure and FigureCanvasQTAgg."""
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        self._figure = Figure(figsize=self._figsize, dpi=self._dpi)
        self._figure.patch.set_facecolor("#1e1e2e")
        self._canvas = FigureCanvasQTAgg(self._figure)

        # Replace placeholder with canvas
        self._placeholder.setVisible(False)
        self._layout.removeWidget(self._placeholder)
        self._placeholder.deleteLater()
        self._placeholder = None
        self._layout.addWidget(self._canvas)

    def draw(self):
        """Redraw the canvas (no-op if not yet materialized)."""
        if self._canvas is not None:
            self._canvas.draw()

    def draw_idle(self):
        """Schedule a deferred redraw (no-op if not yet materialized)."""
        if self._canvas is not None:
            self._canvas.draw_idle()

    def setMinimumHeight(self, h: int):
        super().setMinimumHeight(h)
        if self._canvas is not None:
            self._canvas.setMinimumHeight(h)

    def mpl_connect(self, *args, **kwargs):
        """Connect matplotlib event (creates canvas if needed)."""
        if self._canvas is None:
            self._materialize()
        return self._canvas.mpl_connect(*args, **kwargs)

    def savefig(self, *args, **kwargs):
        """Save the figure (creates canvas if needed)."""
        if self._figure is not None:
            self._figure.savefig(*args, **kwargs)

    @property
    def is_materialized(self) -> bool:
        return self._canvas is not None
