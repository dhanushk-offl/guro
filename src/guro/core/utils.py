from collections import deque


class ASCIIGraph:
    """A clean multi-line block chart rendered inside a Rich Panel.

    No internal border is drawn — the wrapping Rich Panel provides the frame.
    Each sample is drawn as a vertical bar so the trend stays visible even for
    small fluctuations. Values are expected in the 0-100 range.
    """

    def __init__(self, width=40, height=5):
        self.width = width
        self.height = height
        self.data = deque(maxlen=width)
        self.chars = ' ▁▂▃▄▅▆▇█'

    def add_point(self, value):
        self.data.append(value)

    def render(self, title=""):
        if not self.data:
            return ""

        h = max(self.height, 1)
        values = list(self.data)[-self.width:]

        # Build one column per sample; bottom-anchored bars with partial fill
        columns = []
        for val in values:
            scaled = (val / 100.0) * (h * 8)
            full = int(scaled // 8)
            partial = int(scaled % 8)
            col = [' '] * h
            for row in range(h - full, h):
                col[row] = '█'
            if partial > 0 and h - full - 1 >= 0:
                col[h - full - 1] = self.chars[partial]
            columns.append(col)

        lines = []
        if title:
            lines.append(title)
        for row in range(h):
            lines.append(''.join(col[row] for col in columns))
        return '\n'.join(lines)
