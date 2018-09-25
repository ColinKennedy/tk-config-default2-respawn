# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import __builtin__
import keyword as py_keywords

from sgtk.platform.qt import QtCore, QtGui

# based on: https://wiki.python.org/moin/PyQt/Python%20syntax%20highlighting
# TODO: this is the same code as the tk-multi-pythonconsole. need to consolidate

def _format(color, style=''):
    """Return a QtGui.QTextCharFormat with the given attributes.
    """

    _format = QtGui.QTextCharFormat()
    _format.setForeground(color)
    if 'bold' in style:
        _format.setFontWeight(QtGui.QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)

    return _format


class PythonSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax highlighter for the Python language."""


    # Python keywords
    keywords = py_keywords.kwlist

    # Python builtins
    builtins = dir(__builtin__)

    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        '\+', '-', '\*', '/', '//', '\%', '\*\*',
        # In-place
        '\+=', '-=', '\*=', '/=', '\%=',
        # Bitwise
        '\^', '\|', '\&', '\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        '\{', '\}', '\(', '\)', '\[', '\]',
    ]

    def __init__(self, document, palette):
        QtGui.QSyntaxHighlighter.__init__(self, document)

        self._palette = palette

        # Multi-line strings (expression, flag, style)
        # FIXME: The triple-quotes in these two lines will mess up the
        # syntax highlighting from this point onward
        self.tri_single = (QtCore.QRegExp("'''"), 1, self._style("string2"))
        self.tri_double = (QtCore.QRegExp('"""'), 2, self._style("string2"))

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, self._style("keyword"))
            for w in PythonSyntaxHighlighter.keywords]
        rules += [(r'\b%s\b' % w, 0, self._style("builtin"))
            for w in PythonSyntaxHighlighter.builtins]
        rules += [(r'%s' % o, 0, self._style("operator"))
            for o in PythonSyntaxHighlighter.operators]
        rules += [(r'%s' % b, 0, self._style("brace"))
            for b in PythonSyntaxHighlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, self._style("self")),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self._style("string")),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self._style("string")),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, self._style("defclass")),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, self._style("defclass")),

            # From '#' until a newline
            (r'#[^\n]*', 0, self._style("comment")),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, self._style("numbers")),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, self._style("numbers")),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, self._style("numbers")),
        ]

        # Build a QtCore.QRegExp for each pattern
        self.rules = [(QtCore.QRegExp(pat), index, fmt)
            for (pat, index, fmt) in rules]

    def _style(self, style_type):

        palette = self._palette

        styles = {
            'keyword': _format(
                colorize(
                    palette.windowText().color(), 3,
                    QtGui.QColor(0, 0, 255), 1,
                ),
                style="",
            ),
            'builtin': _format(
                colorize(
                    palette.windowText().color(), 3,
                    QtGui.QColor(0, 255, 0), 1,
                ),
                style="",
            ),
            'operator': _format(
                colorize(
                    palette.windowText().color(), 4,
                    palette.highlight().color(), 2,
                ),
                style="",
            ),
            'brace':_format(
                colorize(
                    palette.windowText().color(), 2,
                    palette.base().color(), 1,
                ),
                style="bold",
            ),
            'defclass':_format(
                colorize(
                    palette.windowText().color(), 3,
                    QtGui.QColor(255, 0, 0), 1,
                ),
                style="bold",
            ),
            'string': _format(
                colorize(
                    palette.windowText().color(), 2,
                    palette.highlight().color(), 1,
                ),
                style="bold",
            ),
            'string2': _format(
                colorize(
                    palette.windowText().color(), 1,
                    palette.base().color(), 1,
                ),
                style="",
            ),
            'comment':_format(
                colorize(
                    palette.windowText().color(), 1,
                    palette.base().color(), 2,
                ),
                style="italic",
            ),
            'self': _format(
                colorize(
                    palette.windowText().color(), 1,
                    QtGui.QColor(127, 127, 127), 1,
                ),
                 style="",
            ),
            'numbers': _format(
                colorize(
                    palette.windowText().color(), 3,
                    QtGui.QColor(127, 127, 127), 1,
                ),
                style="",
            ),
        }

        return styles[style_type]

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        # Do other syntax formatting
        for expression, nth, format in self.rules:
            index = expression.indexIn(text, 0)

            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)


    def match_multiline(self, text, delimiter, in_state, style):
        """Do highlighting of multi-line strings. ``delimiter`` should be a
        ``QtCore.QRegExp`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.indexIn(text)
            # Move past this match
            add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.indexIn(text, start + add)
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False

# TODO: this should be a method in shotgunutils soon (color_mix)
def colorize(c1, c1_strength, c2, c2_strength):
    """Convenience method for making a color from 2 existing colors.
    :param c1: QtGui.QColor 1
    :param c1_strength: int factor of the strength of this color
    :param c2: QtGui.QColor 2
    :param c2_strength: int factor of the strength of this color
    This is primarily used to prevent hardcoding of colors that don't work in
    other color palettes. The idea is that you can provide a color from the
    current widget palette and shift it toward another color. For example,
    you could get a red-shifted text color by supplying the windowText color
    for a widget as color 1, and the full red as color 2. Then use the strength
    args to weight the resulting color more toward the windowText or full red.
    It's still important to test the resulting colors in multiple color schemes.
    """

    total = c1_strength + c2_strength

    r = ((c1.red() * c1_strength) + (c2.red() * c2_strength)) / total
    g = ((c1.green() * c1_strength) + (c2.green() * c2_strength)) / total
    b = ((c1.blue() * c1_strength) + (c2.blue() * c2_strength)) / total

    return QtGui.QColor(r, g, b)
