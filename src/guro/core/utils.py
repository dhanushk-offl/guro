from collections import deque

class ASCIIGraph:
    def __init__(self, width=70, height=10):
        self.width = width
        self.height = height
        self.data = deque(maxlen=width)
        self.chars = ' ▁▂▃▄▅▆▇█'

    def add_point(self, value):
        self.data.append(value)

    def render(self, title=""):
        if not self.data:
            return ""

        # Normalize data (0-100 range for percentages/temps)
        normalized = []
        for val in self.data:
            # Scale 0-100 to index 0-len(chars)-1
            idx = int((val / 100.0) * (len(self.chars) - 1))
            normalized.append(max(0, min(len(self.chars) - 1, idx)))

        # Generate graph
        lines = []
        lines.append("╔" + "═" * (self.width + 2) + "╗")
        lines.append("║ " + title.center(self.width) + " ║")
        lines.append("║ " + "─" * self.width + " ║")

        graph_str = ""
        for val in normalized:
            graph_str += self.chars[val]
        lines.append("║ " + graph_str.ljust(self.width) + " ║")
        
        lines.append("╚" + "═" * (self.width + 2) + "╝")
        return "\n".join(lines)
