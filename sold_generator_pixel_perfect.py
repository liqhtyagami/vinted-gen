# sold_generator_pixel_perfect.py
from PIL import Image, ImageDraw, ImageFont
import numpy as np, os

# ---------- CONFIG ----------
TEMPLATE_PATH = "vinted no text.png"
REFERENCE_PATH = "original vinted listing.png"
FONT_REGULAR_PATH = "Roboto-Regular.ttf"
FONT_MEDIUM_PATH = "Roboto-Medium.ttf"
OUT_PATH = "sold_image.png"
BANNER_PATH = "banner.png"
BADGE_PATH = "badge.png"

# Colors
COLOR_WHITE = (255, 255, 251)
COLOR_GRAY = (209, 220, 218)
COLOR_BRAND = (51, 146, 155)
COLOR_PROTECTION = (51, 146, 155)

# ---------- MEASUREMENT HELPERS ----------
def find_green_band(arr):
    h = arr.shape[0]
    rows = []
    for y in range(h):
        row = arr[y, :, :]
        mask = (row[:, 1] > 100) & (row[:, 0] < 90) & (row[:, 2] < 110)
        if mask.mean() > 0.18:
            rows.append(y)
    if not rows:
        raise RuntimeError("Could not find green banner in reference image.")
    return min(rows), max(rows)

def cluster_rows(rows):
    rows = sorted(list(rows))
    groups = []
    if not rows:
        return []
    cur = [rows[0]]
    for r in rows[1:]:
        if r == cur[-1] + 1:
            cur.append(r)
        else:
            groups.append(cur)
            cur = [r]
    groups.append(cur)
    return [((min(g)+max(g))//2, min(g), max(g), len(g)) for g in groups]

def measure_reference(ref_path):
    im = Image.open(ref_path).convert("RGB")
    w, h = im.size
    arr = np.array(im)

    top, bottom = find_green_band(arr)
    band = arr[top:bottom+1, :, :]

    mask_white = (band[:, :, 0] > 200) & (band[:, :, 1] > 200) & (band[:, :, 2] > 200)
    cols_frac = mask_white.mean(axis=0)
    white_cols = np.where(cols_frac > 0.01)[0]
    pad_left = int(white_cols.min()) if len(white_cols) > 0 else 46

    start = bottom + 1
    area = arr[start:, :, :]
    white_row_frac = ((area[:, :, 0] > 200) & (area[:, :, 1] > 200) & (area[:, :, 2] > 200)).mean(axis=1)
    white_rows = np.where(white_row_frac > 0.005)[0] + start
    white_groups = cluster_rows(white_rows)

    cyan_mask = (area[:, :, 1] > 110) & (area[:, :, 2] > 120) & (area[:, :, 0] < 100)
    cyan_row_frac = cyan_mask.mean(axis=1)
    cyan_rows = np.where(cyan_row_frac > 0.002)[0] + start
    cyan_groups = cluster_rows(cyan_rows)

    title_centroids = [white_groups[0][0], white_groups[1][0]] if len(white_groups) >= 2 else [start+40, start+90]
    cond_centroid = white_groups[5][0] if len(white_groups) > 5 else (cyan_groups[0][0] if cyan_groups else (start+150))
    brand_centroid = cyan_groups[0][0] if cyan_groups else cond_centroid
    price_centroid = white_groups[-1][0] if white_groups else start+220
    total_centroid = cyan_groups[-1][0] if cyan_groups else price_centroid + 60

    return {
        "product_box": (0, 0, w, top),
        "sold_banner": {"y": top, "height": bottom - top + 1, "padding_left": pad_left},
        "title_centroids": title_centroids,
        "cond_centroid": cond_centroid,
        "brand_centroid": brand_centroid,
        "price_centroid": price_centroid,
        "total_centroid": total_centroid,
        "canvas_size": (w, h)
    }

# ---------- DRAW HELPERS ----------
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def place_image_in_box(base, product_img_path, box, border_px=None):
    x0, y0, x1, y1 = box
    box_w = x1 - x0
    box_h = y1 - y0
    prod = Image.open(product_img_path).convert("RGB")
    pw, ph = prod.size

    target_ratio = box_w / box_h
    prod_ratio = pw / ph

    if prod_ratio > target_ratio:
        new_w = int(ph * target_ratio)
        left = (pw - new_w) // 2
        prod = prod.crop((left, 0, left + new_w, ph))
    else:
        new_h = int(pw / target_ratio)
        top = (ph - new_h) // 2
        prod = prod.crop((0, top, pw, top + new_h))

    prod = prod.resize((box_w, box_h), Image.LANCZOS)
    base.paste(prod, (x0, y0))
    return base

def generate_sold_image(
    template_path, measurements, product_file, title, condition, brand,
    price, total, badge_scale=1.0, badge_y_offset=0, dot_y_offset=5
):
    tpl = Image.open(template_path).convert("RGB")
    w, h = measurements["canvas_size"]
    if tpl.size != (w, h):
        tpl = tpl.resize((w, h), Image.LANCZOS)

    out = tpl.copy()
    out = place_image_in_box(out, product_file, measurements["product_box"], border_px=6)
    draw = ImageDraw.Draw(out)

    # Fonts
    font_title_first = load_font(FONT_MEDIUM_PATH, 45)  # title regular
    font_title_rest = load_font(FONT_MEDIUM_PATH, 45)   # title regular
    font_medium_regular = load_font(FONT_REGULAR_PATH, 45)  # others mediu
    font_price = load_font(FONT_REGULAR_PATH, 40)
    font_total = load_font(FONT_REGULAR_PATH, 45)
    font_dot = load_font(FONT_REGULAR_PATH, 30)

    sb = measurements["sold_banner"]
    banner_img = Image.open(BANNER_PATH).convert("RGBA")
    banner_img = banner_img.resize((w, sb["height"]), Image.LANCZOS)
    out.paste(banner_img, (0, sb["y"]), banner_img)

    # title wrap
    max_width = 980
    words = title.split()
    lines = []
    cur = ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font_title_rest) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
        if len(lines) == 2:
            break
    if cur and len(lines) < 2:
        lines.append(cur)

    for i, line in enumerate(lines[:2]):
        centroid = measurements["title_centroids"][i]
        font = font_title_first if i == 0 else font_title_rest
        bbox = draw.textbbox((0, 0), line, font=font)
        th = bbox[3] - bbox[1]
        y = centroid - th // 2
        draw.text((sb["padding_left"], y), line, font=font, fill=COLOR_WHITE)

    # condition + dot + brand
    cond_cent = measurements["cond_centroid"]
    bbox_cond = draw.textbbox((0, 0), condition, font=font_medium_regular)
    th_cond = bbox_cond[3] - bbox_cond[1]
    y_cond = cond_cent - th_cond // 2

    # Draw condition
    draw.text((sb["padding_left"], y_cond), condition, font=font_medium_regular, fill=COLOR_GRAY)

    # Draw smaller dot
    dot_text = "•"
    dot_w = draw.textlength(dot_text, font=font_dot)
    cond_w = draw.textlength(condition, font=font_medium_regular)
    dot_x = sb["padding_left"] + cond_w + 10
    draw.text((dot_x, y_cond + 5 + dot_y_offset), dot_text, font=font_dot, fill=COLOR_GRAY)

    # Draw brand
    brand_x = dot_x + dot_w + 10
    draw.text((brand_x, y_cond), brand, font=font_medium_regular, fill=COLOR_BRAND)

    # underline brand
    brand_text_w = draw.textlength(brand, font=font_medium_regular)
    brand_y_bottom = y_cond + th_cond + 2
    draw.line(
        [(brand_x, brand_y_bottom), (brand_x + brand_text_w, brand_y_bottom)],
        fill=COLOR_BRAND,
        width=2
    )

    # price in gray
    price_cent = measurements["price_centroid"]
    bbox_price = draw.textbbox((0, 0), f"£{price}", font=font_price)
    th_price = bbox_price[3] - bbox_price[1]
    y_price = price_cent - th_price // 2
    draw.text((sb["padding_left"], y_price), f"£{price}", font=font_price, fill=COLOR_GRAY)

    # total + buyer protection
    tot_cent = measurements["total_centroid"]
    buyer_text = f"£{total} Includes Buyer Protection"
    bbox_tot = draw.textbbox((0, 0), buyer_text, font=font_total)
    th_tot = bbox_tot[3] - bbox_tot[1]
    y_tot = tot_cent - th_tot // 2
    draw.text((sb["padding_left"], y_tot), buyer_text, font=font_total, fill=COLOR_PROTECTION)

    # badge
    badge_img = Image.open(BADGE_PATH).convert("RGBA")
    base_badge_size = 60
    badge_size = int(base_badge_size * badge_scale)
    badge_img = badge_img.resize((badge_size, badge_size), Image.LANCZOS)
    text_width = draw.textlength(buyer_text, font=font_total)
    badge_x = sb["padding_left"] + text_width + 4
    badge_y = y_tot + badge_y_offset
    out.paste(badge_img, (int(badge_x), int(badge_y)), badge_img)

    return out

# ---------- MAIN ----------
if __name__ == "__main__":
    measurements = measure_reference(REFERENCE_PATH)
    product_path = "product.jpg"
    result = generate_sold_image(
        TEMPLATE_PATH,
        measurements,
        product_path,
        title="Van Cleef & Arpels Malachite Vintage Alhambra 5 Motif Bracelet.",
        condition="Very good",
        brand="Van Cleef & Arpels",
        price="400.00",
        total="420.70",
        badge_scale=2.0,
        badge_y_offset=30,
        dot_y_offset=30
    )
    result.save(OUT_PATH)
    print("Saved:", OUT_PATH)
