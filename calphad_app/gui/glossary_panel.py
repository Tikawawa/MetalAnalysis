"""Searchable glossary dock widget for metallurgy and CALPHAD terms."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QListWidget, QTextBrowser, QSplitter,
)

from gui.info_content import GLOSSARY


class GlossaryPanel(QDockWidget):
    """Dock widget providing a searchable glossary of metallurgy and
    thermodynamic terms with cross-referenced 'see also' links."""

    def __init__(self, parent=None):
        super().__init__("Glossary", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumWidth(300)
        self._sorted_terms: list[str] = sorted(GLOSSARY.keys(), key=str.lower)
        self._setup_ui()
        self._populate_list(self._sorted_terms)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        container = QWidget()
        container.setStyleSheet("background-color: #1a1a2e; color: #e0e0e0;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel("Glossary")
        header.setStyleSheet(
            "color: #4FC3F7; font-size: 14px; font-weight: bold; padding: 2px;"
        )
        layout.addWidget(header)

        # Search bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search terms...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setStyleSheet(
            "QLineEdit { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; padding: 6px; "
            "font-size: 13px; }"
            "QLineEdit:focus { border-color: #4FC3F7; }"
        )
        self.search_box.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_box)

        # Splitter: term list + definition browser
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet(
            "QSplitter::handle { background-color: #333355; height: 2px; }"
        )

        self.term_list = QListWidget()
        self.term_list.setStyleSheet(
            "QListWidget { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; font-size: 13px; }"
            "QListWidget::item { padding: 4px 8px; }"
            "QListWidget::item:selected { background-color: #0f3460; color: #4FC3F7; }"
            "QListWidget::item:hover { background-color: #1a2a4e; }"
        )
        self.term_list.currentTextChanged.connect(self._on_term_selected)
        splitter.addWidget(self.term_list)

        self.definition_browser = QTextBrowser()
        self.definition_browser.setOpenLinks(False)
        self.definition_browser.setStyleSheet(
            "QTextBrowser { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; padding: 8px; "
            "font-size: 13px; }"
        )
        self.definition_browser.setPlaceholderText(
            "Select a term from the list to see its definition."
        )
        self.definition_browser.anchorClicked.connect(self._on_link_clicked)
        splitter.addWidget(self.definition_browser)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)

        # Term count
        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #666688; font-size: 11px; padding: 2px;")
        self._update_count(len(self._sorted_terms))
        layout.addWidget(self.count_label)

        self.setWidget(container)

    # ------------------------------------------------------------------
    # List population and filtering
    # ------------------------------------------------------------------

    def _populate_list(self, terms: list[str]):
        """Fill the list widget with the given term names."""
        self.term_list.clear()
        for term in terms:
            self.term_list.addItem(term)
        self._update_count(len(terms))

    def _update_count(self, visible: int):
        total = len(self._sorted_terms)
        if visible == total:
            self.count_label.setText(f"{total} terms")
        else:
            self.count_label.setText(f"Showing {visible} of {total} terms")

    def _on_search_changed(self, text: str):
        """Filter the term list in real-time as the user types."""
        query = text.strip().lower()
        if not query:
            self._populate_list(self._sorted_terms)
            return
        matched = [
            t for t in self._sorted_terms
            if query in t.lower() or query in GLOSSARY[t]["definition"].lower()
        ]
        self._populate_list(matched)

    # ------------------------------------------------------------------
    # Term display
    # ------------------------------------------------------------------

    def _on_term_selected(self, term_name: str):
        """Display the definition for the selected term."""
        if not term_name or term_name not in GLOSSARY:
            return
        self._show_definition(term_name)

    def _show_definition(self, term_name: str):
        """Render the definition as styled HTML in the text browser."""
        entry = GLOSSARY.get(term_name)
        if entry is None:
            self.definition_browser.setHtml(
                '<p style="color: #E57373;">Term not found.</p>'
            )
            return

        see_also = entry.get("see_also", [])
        html = (
            f'<h2 style="color: #4FC3F7;">{term_name}</h2>'
            f'<p style="color: #e0e0e0; font-size: 14px; line-height: 1.6;">'
            f'{entry["definition"]}</p>'
        )
        if see_also:
            links = ", ".join(
                f'<a href="#{ref}" style="color: #81C784;">{ref}</a>'
                for ref in see_also
            )
            html += (
                f'<p style="color: #888; font-size: 12px;">'
                f'See also: {links}</p>'
            )
        self.definition_browser.setHtml(html)

    def _on_link_clicked(self, url: QUrl):
        """Handle clicks on 'see also' links by selecting the referenced term."""
        fragment = url.fragment()
        if not fragment:
            raw = url.toString()
            fragment = raw[1:] if raw.startswith("#") else raw
        if fragment in GLOSSARY:
            self._select_term(fragment)

    def _select_term(self, term_name: str):
        """Programmatically select a term, clearing the search filter first."""
        self.search_box.clear()
        for i in range(self.term_list.count()):
            item = self.term_list.item(i)
            if item is not None and item.text() == term_name:
                self.term_list.setCurrentItem(item)
                self.term_list.scrollToItem(item)
                break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup_term(self, term_name: str):
        """Programmatically look up and display a glossary term.

        Parameters
        ----------
        term_name : str
            The glossary term to display. Must match a key in GLOSSARY.
        """
        if term_name in GLOSSARY:
            self._select_term(term_name)
        else:
            self.definition_browser.setHtml(
                f'<p style="color: #E57373;">Term "{term_name}" not found '
                f'in glossary.</p>'
            )
