from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0D0D0D"
ACCENT = "#059669"
ACCENT_LIGHT = "#34D399"
TEXT = "#FFFFFF"
MUTED = "#8E8E93"
DIM = "#636366"
SURFACE = "#1C1C1E"
BORDER = "#2C2C2E"

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

try:
    font_bold = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 64)
    font_mono = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf", 24)
    font_mono_sm = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 18)
    font_sans = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 28)
    font_sans_sm = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 20)
except:
    font_bold = font_mono = font_mono_sm = font_sans = font_sans_sm = ImageFont.load_default()

# subtle grid dots
dot_color = (30, 30, 30)
for x in range(0, W, 20):
    for y in range(0, H, 20):
        draw.point((x, y), fill=dot_color)

# terminal window
term_w, term_h = 680, 380
term_x, term_y = 60, 140
draw.rounded_rectangle(
    [(term_x, term_y), (term_x + term_w, term_y + term_h)],
    radius=12, fill=SURFACE, outline=BORDER, width=1
)

# title bar dots
dot_positions = [(term_x + 18, term_y + 16), (term_x + 36, term_y + 16), (term_x + 54, term_y + 16)]
dot_colors = ["#f87171", "#fbbf24", "#34d399"]
for (dx, dy), dc in zip(dot_positions, dot_colors):
    draw.ellipse([(dx - 5, dy - 5), (dx + 5, dy + 5)], fill=dc)

# terminal title
draw.text((term_x + 80, term_y + 9), "guro — system-monitor", fill=DIM, font=font_mono_sm)

# terminal content
content_x, content_y = term_x + 24, term_y + 48
line_h = 32

lines = [
    (None, None),
    ("$", " pip install guro", None, ACCENT_LIGHT),
    (None, None),
    ("  ", "Collecting guro...", None, DIM),
    ("  ", "Successfully installed guro", None, ACCENT_LIGHT),
    (None, None),
    ("$", " guro monitor", None, ACCENT_LIGHT),
    (None, None),
    ("  ", "Initializing dashboard...", None, "#fb923c"),
    ("  ", "CPU  ████████████░░░  78%", None, DIM),
    ("  ", "MEM  ██████░░░░░░░░░  42%", None, DIM),
    ("  ", "GPU  ████████░░░░░░  65%", None, ACCENT_LIGHT),
]

y = content_y
for parts in lines:
    if parts[0] is None:
        y += line_h * 0.6
        continue
    prompt, cmd, _, color = parts
    if prompt == "$":
        draw.text((content_x, y), "$", fill=ACCENT_LIGHT, font=font_mono_sm)
        draw.text((content_x + 16, y), cmd, fill=TEXT, font=font_mono_sm)
    else:
        draw.text((content_x, y), prompt + cmd, fill=color, font=font_mono_sm)
    y += line_h

# blinking cursor at end
cx = content_x + 16
cy = y
draw.rectangle([(cx, cy), (cx + 8, cy + 20)], fill=ACCENT_LIGHT)

# brand on right side
brand_x = term_x + term_w + 50

draw.text((brand_x, 220), "[ guro ]", fill=ACCENT_LIGHT, font=font_bold)

tag_y = 300
draw.rounded_rectangle([(brand_x, tag_y), (brand_x + 240, tag_y + 40)], radius=20, fill=ACCENT)
draw.text((brand_x + 120, tag_y + 20), "CLI SYSTEM TOOLKIT", fill=TEXT, font=font_sans_sm, anchor="mm")

sub_y = 370
for line in ["Real-time CPU · GPU · Memory", "Thermal · Network · Benchmark"]:
    draw.text((brand_x, sub_y), line, fill=MUTED, font=font_sans_sm)
    sub_y += 32

# platform badges
platforms = ["Linux", "macOS", "Windows", "ARM"]
px = brand_x
py_val = 460
for p in platforms:
    draw.rounded_rectangle([(px, py_val), (px + 80, py_val + 32)], radius=16, fill="#1C1C1E", outline="#2C2C2E", width=1)
    draw.text((px + 40, py_val + 16), p, fill=MUTED, font=font_mono_sm, anchor="mm")
    px += 92

# bottom bar
draw.line([(0, H - 56), (W, H - 56)], fill=BORDER, width=1)
draw.text((40, H - 36), "Open Source · MIT License", fill=DIM, font=font_sans_sm)
draw.text((W - 40, H - 36), "guro.pages.dev", fill=ACCENT, font=font_mono_sm, anchor="rs")

output_path = "/home/dhanush/guro/docs/web/og-image.png"
img.save(output_path, quality=95, optimize=True)
print(f"OG image saved: {output_path} ({img.size[0]}x{img.size[1]})")
