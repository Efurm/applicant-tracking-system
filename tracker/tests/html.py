"""Helpers for asserting on rendered HTML in tests."""

from html.parser import HTMLParser


class _MarkedElements(HTMLParser):
    """Collects the attributes and text of every element that carries ``attr``."""

    VOID = {"area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}

    def __init__(self, attr):
        super().__init__()
        self.attr = attr
        self.found = []
        self._open = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        entry = {"attrs": attrs, "text": ""} if self.attr in attrs else None
        if entry is not None:
            self.found.append(entry)
        if tag not in self.VOID:
            self._open.append(entry)

    def handle_endtag(self, tag):
        if tag not in self.VOID and self._open:
            self._open.pop()

    def handle_data(self, data):
        for entry in self._open:
            if entry is not None:
                entry["text"] += data


def marked(response, attr):
    """[(attr value, all attributes, whitespace-collapsed text)] for elements with ``attr``."""
    parser = _MarkedElements(attr)
    parser.feed(response.content.decode())
    return [(e["attrs"][attr], e["attrs"], " ".join(e["text"].split())) for e in parser.found]
