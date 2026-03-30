"""Lazy matplotlib canvas that only creates FigureCanvasQTAgg on first use.

This prevents segfaults from having too many active matplotlib canvases
in a PyQt6 tab widget. The crash occurs when Qt repaints canvases on hidden
tabs during rapid tab switching.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
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

        # Expanding size policy so canvas fills available space
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Placeholder shown until first use
        self._placeholder = QLabel("Run a calculation to see the plot here")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #555577; font-size: 14px; font-style: italic; "
            "background-color: #1e1e2e; border: 1px dashed #333355; "
            "border-radius: 4px; padding: 20px;"
        )
        self._layout.addWidget(self._placeholder)

        # Line hover state
        self._hover_enabled = False
        self._hover_annotation = None
        self._original_line_styles: dict[int, tuple] = {}  # id -> (lw, alpha)
        self._legend_texts: list = []
        self._legend_lines: list = []

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
        self._canvas.setCursor(QCursor(Qt.CursorShape.CrossCursor))

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

    def sizeHint(self) -> QSize:
        w = int(self._figsize[0] * self._dpi)
        h = int(self._figsize[1] * self._dpi)
        return QSize(w, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._canvas is not None and event.size().width() > 0 and event.size().height() > 0:
            w = event.size().width()
            h = event.size().height()
            self._figure.set_size_inches(w / self._dpi, h / self._dpi, forward=True)
            self._canvas.draw_idle()

    # ------------------------------------------------------------------
    # Interactive line hover + legend click (Fixes 1, 2, 15)
    # ------------------------------------------------------------------

    def enable_line_hover(self):
        """Enable hover-to-highlight and click-to-toggle on all Line2D artists.

        Call this AFTER plotting is complete and canvas.draw() has been called.
        Sets up:
        - Hover near a line: thickens it, dims others, bolds legend entry,
          shows annotation with label + value.
        - Click a legend entry: toggles that line's visibility.
        """
        if not self.is_materialized:
            return
        self._hover_enabled = True
        self._hover_annotation = None
        self._original_line_styles.clear()
        self._legend_texts.clear()
        self._legend_lines.clear()

        # Cache original line styles
        for ax in self._figure.get_axes():
            for line in ax.get_lines():
                self._original_line_styles[id(line)] = (
                    line.get_linewidth(),
                    line.get_alpha() if line.get_alpha() is not None else 1.0,
                )

        # Make legend items pickable
        for ax in self._figure.get_axes():
            legend = ax.get_legend()
            if legend is not None:
                for leg_line, leg_text in zip(
                    legend.get_lines(), legend.get_texts()
                ):
                    leg_line.set_picker(5)
                    self._legend_lines.append(leg_line)
                    self._legend_texts.append(leg_text)

        self._canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._canvas.mpl_connect("pick_event", self._on_legend_pick)

    def _on_hover(self, event):
        """Highlight nearest line and show value tooltip on hover."""
        if not self._hover_enabled or event.inaxes is None:
            self._restore_lines()
            self._hide_hover_annotation()
            self._canvas.draw_idle()
            return

        ax = event.inaxes
        lines = [
            ln for ln in ax.get_lines()
            if ln.get_visible() and ln.get_label() and not ln.get_label().startswith("_")
        ]
        if not lines:
            return

        # Find nearest line
        best_line = None
        best_dist = float("inf")
        best_idx = 0

        # Get axis data-to-display transform for proper distance calc
        x_display, y_display = ax.transData.transform((event.xdata, event.ydata))

        for line in lines:
            xdata, ydata = line.get_xdata(), line.get_ydata()
            if len(xdata) == 0:
                continue
            # Transform line data to display coords for distance
            xy = ax.transData.transform(np.column_stack([xdata, ydata]))
            dists = np.sqrt((xy[:, 0] - x_display) ** 2 + (xy[:, 1] - y_display) ** 2)
            min_idx = np.argmin(dists)
            d = dists[min_idx]
            if d < best_dist:
                best_dist = d
                best_line = line
                best_idx = min_idx

        # 15 pixel threshold
        if best_line is None or best_dist > 15:
            self._restore_lines()
            self._hide_hover_annotation()
            self._canvas.draw_idle()
            return

        # Highlight best line, dim others
        for ln in lines:
            orig = self._original_line_styles.get(id(ln))
            if orig is None:
                continue
            if ln is best_line:
                ln.set_linewidth(orig[0] * 2.5)
                ln.set_alpha(1.0)
            else:
                ln.set_linewidth(orig[0])
                ln.set_alpha(0.25)

        # Bold the matching legend entry
        legend = ax.get_legend()
        if legend is not None:
            for leg_line, leg_text in zip(legend.get_lines(), legend.get_texts()):
                label = leg_text.get_text()
                if label == best_line.get_label():
                    leg_text.set_fontweight("bold")
                    leg_text.set_color("#ffffff")
                    leg_line.set_linewidth(3)
                else:
                    leg_text.set_fontweight("normal")
                    leg_text.set_color("#cccccc")
                    leg_line.set_linewidth(1.5)

        # Show annotation with value
        xval = best_line.get_xdata()[best_idx]
        yval = best_line.get_ydata()[best_idx]
        label = best_line.get_label()
        text = f"{label}\nx={xval:.4g}  y={yval:.4g}"

        if self._hover_annotation is None or self._hover_annotation.axes is not ax:
            if self._hover_annotation is not None:
                try:
                    self._hover_annotation.remove()
                except Exception:
                    pass
            self._hover_annotation = ax.annotate(
                text,
                xy=(xval, yval),
                xytext=(12, 12),
                textcoords="offset points",
                fontsize=9,
                color="white",
                bbox=dict(
                    boxstyle="round,pad=0.4",
                    facecolor="#2d2d3e",
                    edgecolor="#4FC3F7",
                    alpha=0.95,
                ),
                arrowprops=dict(arrowstyle="-", color="#4FC3F7", lw=0.8),
                zorder=999,
            )
        else:
            self._hover_annotation.set_text(text)
            self._hover_annotation.xy = (xval, yval)
            self._hover_annotation.set_visible(True)

        self._canvas.draw_idle()

    def _restore_lines(self):
        """Restore all lines to their original styles."""
        if not self._figure:
            return
        for ax in self._figure.get_axes():
            for line in ax.get_lines():
                orig = self._original_line_styles.get(id(line))
                if orig:
                    line.set_linewidth(orig[0])
                    line.set_alpha(orig[1])
            legend = ax.get_legend()
            if legend is not None:
                for leg_line, leg_text in zip(legend.get_lines(), legend.get_texts()):
                    leg_text.set_fontweight("normal")
                    leg_text.set_color("white")
                    leg_line.set_linewidth(1.5)

    def _hide_hover_annotation(self):
        """Hide the hover value annotation."""
        if self._hover_annotation is not None:
            self._hover_annotation.set_visible(False)

    def _on_legend_pick(self, event):
        """Toggle line visibility when its legend entry is clicked."""
        if not self._hover_enabled:
            return
        leg_artist = event.artist
        # Find which legend line was clicked
        for ax in self._figure.get_axes():
            legend = ax.get_legend()
            if legend is None:
                continue
            for leg_line, leg_text, orig_line in zip(
                legend.get_lines(), legend.get_texts(), ax.get_lines()
            ):
                if leg_line is not leg_artist:
                    continue
                # Match by label since legend order may differ
                target_label = leg_text.get_text()
                for line in ax.get_lines():
                    if line.get_label() == target_label:
                        vis = not line.get_visible()
                        line.set_visible(vis)
                        leg_text.set_alpha(1.0 if vis else 0.3)
                        leg_line.set_alpha(1.0 if vis else 0.3)
                        break
                self._canvas.draw_idle()
                return
