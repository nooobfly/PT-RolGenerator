import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageFont

BADGE_HEIGHT  = 32
ICON_SIZE     = 32
H_PADDING     = 8
CORNER_RADIUS = 8
ICON_BG_COLOR = (55, 57, 63)
BG_COLOR      = (45, 45, 50)
ICON_TAG_GAP  = 2

GLOSS_SPACING = 34
GLOSS_PHASE   = GLOSS_SPACING // 2

HIGHLIGHT     = (80, 82, 90, 200)
SHADOW_INNER  = (10, 10, 12, 220)
DROP_OFFSET   = 2
DROP_BLUR     = 0
DROP_COLOR    = (0, 0, 0, 220)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
FULL_DIR = Path("FullOutput")
FULL_DIR.mkdir(exist_ok=True)
SCRIPT_DIR = Path(__file__).parent


def load_svg_as_image(svg_path: Path, size: int) -> Image.Image:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vw = int(root.get("width", 64))
    vh = int(root.get("height", 64))

    scale = max(1, (size * 4) // max(vw, vh))
    rw, rh = vw * scale, vh * scale
    img = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for rect in root.findall(".//{http://www.w3.org/2000/svg}rect") + root.findall(".//rect"):
        x = int(float(rect.get("x", 0))) * scale
        y = int(float(rect.get("y", 0))) * scale
        w = int(float(rect.get("width", 1))) * scale
        h = int(float(rect.get("height", 1))) * scale
        fill = rect.get("fill", "#000000")
        r, g, b = int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16)
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=(r, g, b, 255))

    if img.width != size or img.height != size:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def load_font(size: int = 11):
    candidates = [
        "ari.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_pixel_text(draw, text, font, x, y, color):
    mask = font.getmask(text)
    w, h = mask.size
    for py in range(h):
        for px in range(w):
            if mask.getpixel((px, py)) > 128:
                draw.point((x + px, y + py), fill=color)


def crisp_alpha(img: Image.Image, threshold: int = 160) -> Image.Image:
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= threshold else 0)
    img = img.copy()
    img.putalpha(a)
    return img


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    for cx, cy in [(x0, y0), (x1 - radius*2, y0),
                   (x0, y1 - radius*2), (x1 - radius*2, y1 - radius*2)]:
        draw.ellipse([cx, cy, cx + radius*2, cy + radius*2], fill=fill)


def add_drop_shadow(img: Image.Image, offset: int, blur: int, color) -> Image.Image:
    w, h = img.size
    canvas_h = h + offset
    canvas = Image.new("RGBA", (w, canvas_h), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (w, canvas_h), (0, 0, 0, 0))
    mask = img.split()[3]
    colored = Image.new("RGBA", (w, h), color)
    colored.putalpha(mask)
    shadow.paste(colored, (0, offset))

    canvas = Image.alpha_composite(canvas, shadow)
    fg = Image.new("RGBA", (w, canvas_h), (0, 0, 0, 0))
    fg.paste(img, (0, 0))
    canvas = Image.alpha_composite(canvas, fg)
    return canvas


def apply_diagonal_gloss(canvas: Image.Image, shape_mask: Image.Image,
                          band_w=4, skew_ratio=0.7, alpha=90,
                          spacing_px=GLOSS_SPACING, phase=GLOSS_PHASE, origin_x=0):
    w, h = canvas.size
    skew = int(h * skew_ratio)

    gloss_mask = Image.new("L", (w, h), 0)
    gloss_draw = ImageDraw.Draw(gloss_mask)

    first_k = (origin_x - skew - band_w - phase) // spacing_px
    last_k  = (origin_x + w - phase) // spacing_px + 1
    k = int(first_k)
    while k <= last_k:
        global_x = k * spacing_px + phase
        band_x = global_x - origin_x - band_w // 2
        gloss_draw.polygon(
            [
                (band_x + skew, 0),
                (band_x + skew + band_w, 0),
                (band_x + band_w, h - 1),
                (band_x, h - 1),
            ],
            fill=alpha,
        )
        k += 1

    gloss_mask = ImageChops.multiply(gloss_mask, shape_mask)
    gloss_layer = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    canvas.paste(gloss_layer, (0, 0), gloss_mask)
    return canvas


def build_icon_img(icon_path: Path, bg_color=None) -> Image.Image:
    icon_bg = bg_color if bg_color else ICON_BG_COLOR

    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([0, 0, ICON_SIZE - 1, ICON_SIZE - 1], fill=(*icon_bg, 255))

    shadow_h = max(3, ICON_SIZE // 8)
    dark = tuple(max(0, c - 100) for c in icon_bg)
    draw.rectangle([0, ICON_SIZE - shadow_h, ICON_SIZE - 1, ICON_SIZE - 1], fill=(*dark, 255))

    shadow_w = max(2, ICON_SIZE // 12)
    draw.rectangle([ICON_SIZE - shadow_w, 0, ICON_SIZE - 1, ICON_SIZE - 1], fill=(*dark, 255))

    full_mask = Image.new("L", (ICON_SIZE, ICON_SIZE), 255)
    apply_diagonal_gloss(canvas, full_mask, band_w=3, origin_x=0)

    bg_shadowed = canvas

    pad = 4
    inner = min(ICON_SIZE - 2, int((ICON_SIZE - pad * 2) * 1.3))
    if icon_path.suffix.lower() == ".svg":
        icon = load_svg_as_image(icon_path, inner)
    else:
        icon = Image.open(icon_path).convert("RGBA")
        icon = crisp_alpha(icon)
        icon = icon.resize((inner, inner), Image.NEAREST)
    usable_h = ICON_SIZE - shadow_h
    icon_x = (ICON_SIZE - inner) // 2
    icon_y = (usable_h - inner) // 2
    bg_shadowed.paste(icon, (icon_x, icon_y), icon)
    return bg_shadowed


def build_tag_img(label: str, text_color, font, bg_color=None, origin_x=None) -> Image.Image:
    tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp_draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]

    width  = H_PADDING + text_w + H_PADDING
    radius = 3
    bg = bg_color if bg_color else BG_COLOR
    dark = tuple(max(0, c - 100) for c in bg)

    shape_mask = Image.new("L", (width, BADGE_HEIGHT), 0)
    ImageDraw.Draw(shape_mask).rounded_rectangle(
        [0, 0, width - 1, BADGE_HEIGHT - 1], radius=radius, fill=255
    )

    shadow_h = max(3, BADGE_HEIGHT // 8)
    band_mask = Image.new("L", (width, BADGE_HEIGHT), 0)
    ImageDraw.Draw(band_mask).rectangle(
        [0, BADGE_HEIGHT - shadow_h, width - 1, BADGE_HEIGHT - 1], fill=255
    )
    dark_mask = ImageChops.multiply(shape_mask, band_mask)

    tag = Image.new("RGBA", (width, BADGE_HEIGHT), (0, 0, 0, 0))
    bg_layer = Image.new("RGBA", (width, BADGE_HEIGHT), (*bg, 255))
    tag.paste(bg_layer, (0, 0), shape_mask)
    dark_layer = Image.new("RGBA", (width, BADGE_HEIGHT), (*dark, 255))
    tag.paste(dark_layer, (0, 0), dark_mask)

    tag_origin_x = origin_x if origin_x is not None else (ICON_SIZE + ICON_TAG_GAP)
    apply_diagonal_gloss(tag, shape_mask, band_w=4, origin_x=tag_origin_x)

    text_x = H_PADDING
    usable_h = BADGE_HEIGHT - shadow_h
    text_h = bbox[3] - bbox[1]
    text_y = (usable_h - text_h) // 2
    draw = ImageDraw.Draw(tag)
    draw_pixel_text(draw, label, font, text_x + 2, text_y, (0, 0, 0, 255))
    draw_pixel_text(draw, label, font, text_x, text_y, (*text_color, 255))
    return tag


def generate_role(role: dict):
    rid        = role["id"]
    label      = role["label"]
    text_color = hex_to_rgb(role["color"])
    bg_color   = hex_to_rgb(role["bg_color"]) if "bg_color" in role else None
    icon_path  = SCRIPT_DIR / role.get("icon", "")
    font       = load_font(22)

    has_icon = icon_path.exists()

    if has_icon:
        icon_img = build_icon_img(icon_path, bg_color)
        out_icon = OUTPUT_DIR / f"{rid}_ikon.png"
        icon_img.save(out_icon, "PNG")
        print(f"[icon] {out_icon}")

    tag_origin_x = (ICON_SIZE + ICON_TAG_GAP) if has_icon else 0
    tag_img = build_tag_img(label, text_color, font, bg_color, origin_x=tag_origin_x)
    out_tag = OUTPUT_DIR / f"{rid}.png"
    tag_img.save(out_tag, "PNG")
    print(f"[tag ] {out_tag}")

    if has_icon:
        full_w = icon_img.width + ICON_TAG_GAP + tag_img.width
        full_h = max(icon_img.height, tag_img.height)
        combined = Image.new("RGBA", (full_w, full_h), (0, 0, 0, 0))
        combined.paste(icon_img, (0, 0), icon_img)
        combined.paste(tag_img, (icon_img.width + ICON_TAG_GAP, 0), tag_img)

        out_full = FULL_DIR / f"{rid}_full.png"
        combined.save(out_full, "PNG")
        print(f"[full] {out_full}")


def generate_config(roles: list):
    lines = []
    lines.append("info:")
    lines.append("  namespace: portakalrutbeler")
    lines.append("")
    lines.append("font_images:")
    lines.append("  portakalkabuk:")
    lines.append('    permission: "portakalhub.admin.ranksitemsadder"')
    lines.append("    show_in_gui: true")
    lines.append('    path: "font/portakalkabuk.png"')
    lines.append("    scale_ratio: 10")
    lines.append("    y_position: 8")

    for role in roles:
        rid = role["id"]
        has_icon = (SCRIPT_DIR / role.get("icon", "")).exists()

        if has_icon:
            lines.append(f"  {rid}_ikon:")
            lines.append(f'    permission: "portakalhub.admin.ranksitemsadder"')
            lines.append(f"    show_in_gui: true")
            lines.append(f'    path: "font/{rid}_ikon.png"')
            lines.append(f"    scale_ratio: 9")
            lines.append(f"    y_position: 8")

        lines.append(f"  {rid}:")
        lines.append(f'    permission: "portakalhub.admin.ranksitemsadder"')
        lines.append(f"    show_in_gui: true")
        lines.append(f'    path: "font/{rid}.png"')
        lines.append(f"    scale_ratio: 9")
        lines.append(f"    y_position: 8")

    config_path = SCRIPT_DIR / "config.yml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[config] {config_path}")


def main():
    roles_file = SCRIPT_DIR / "roles.json"
    with open(roles_file, encoding="utf-8") as f:
        roles = json.load(f)

    for role in roles:
        generate_role(role)
        print()

    generate_config(roles)
    print(f"Bitti -> {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
