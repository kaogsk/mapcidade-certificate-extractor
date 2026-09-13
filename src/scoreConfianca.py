PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0


def _score_qrcode(width: float, height: float, aspect: float, x: float, y_pct: float) -> float:
    s = 0.0
    if 15 <= width <= 35:
        s += 0.25
    elif 10 <= width <= 40:
        s += 0.10
    if 15 <= height <= 35:
        s += 0.25
    elif 10 <= height <= 40:
        s += 0.10
    # Squareness is the defining feature of QR codes
    if 0.93 <= aspect <= 1.07:
        s += 0.35
    elif 0.85 <= aspect <= 1.15:
        s += 0.15
    elif 0.75 <= aspect <= 1.30:
        s += 0.05
    # QR codes in certificates appear near edges (top/bottom corners)
    x_pct = x / PAGE_WIDTH_MM
    near_edge = x_pct < 0.15 or x_pct > 0.70
    in_qr_zone = y_pct < 0.25 or y_pct > 0.70
    if near_edge and in_qr_zone:
        s += 0.15
    elif near_edge or in_qr_zone:
        s += 0.05
    return min(s, 1.0)


def _score_logo(area: float, y_pct: float, width: float, height: float) -> float:
    s = 0.0
    if area < 800:
        s += 0.35
    elif area < 2000:
        s += 0.20
    elif area < 4000:
        s += 0.08
    # Logos are in the top half of the page
    if y_pct < 0.20:
        s += 0.45
    elif y_pct < 0.35:
        s += 0.40
    elif y_pct < 0.45:
        s += 0.30
    elif y_pct < 0.55:
        s += 0.10
    # Logos are often wider than tall
    aspect = width / height if height > 0 else 0
    if 1.1 <= aspect <= 3.0:
        s += 0.10
    return min(s, 1.0)


def _score_map(area: float, aspect: float, y_pct: float) -> float:
    s = 0.0
    if area > 8000:
        s += 0.4
    elif area > 4000:
        s += 0.2
    if 1.5 <= aspect <= 4.0:
        s += 0.3
    elif 1.2 <= aspect <= 5.0:
        s += 0.1
    if 0.20 <= y_pct <= 0.80:
        s += 0.3
    return min(s, 1.0)


def _score_header(width: float, height: float, y_pct: float) -> float:
    s = 0.0
    if width > PAGE_WIDTH_MM * 0.6:
        s += 0.5
    elif width > PAGE_WIDTH_MM * 0.4:
        s += 0.2
    if y_pct < 0.20:
        s += 0.3
    elif y_pct < 0.30:
        s += 0.1
    if height < 10:
        s += 0.2
    elif height < 20:
        s += 0.1
    return min(s, 1.0)


def _score_footer(width: float, y_pct: float) -> float:
    s = 0.0
    if width > PAGE_WIDTH_MM * 0.3:
        s += 0.5
    elif width > PAGE_WIDTH_MM * 0.2:
        s += 0.2
    if y_pct > 0.85:
        s += 0.5
    elif y_pct > 0.75:
        s += 0.2
    return min(s, 1.0)


def _score_line(width: float, height: float) -> float:
    s = 0.0
    if height < 5:
        s += 0.5
    elif height < 8:
        s += 0.2
    if width > PAGE_WIDTH_MM * 0.5:
        s += 0.5
    elif width > PAGE_WIDTH_MM * 0.3:
        s += 0.2
    return min(s, 1.0)


def _score_image(area: float, y_pct: float, aspect: float, x_pct: float) -> float:
    # Generic embedded images: body area, not near edges, moderate size
    s = 0.0
    if 0.20 <= y_pct <= 0.85:
        s += 0.20
    # Center horizontal position typical for inline body images
    if 0.15 <= x_pct <= 0.75:
        s += 0.25
    if 200 <= area <= 6000:
        s += 0.20
    if 0.5 <= aspect <= 3.0:
        s += 0.10
    return min(s, 0.75)


def score_image_type(
    bbox_mm: dict,
    page_height_mm: float = PAGE_HEIGHT_MM,
    page_width_mm: float = PAGE_WIDTH_MM,
) -> dict:
    """
    Classifica tipo de imagem por scoring multicritério.
    Retorna dict com: type, confidence, scores, flags.
    confidence < 0.65 indica item para revisão manual.
    """
    x = bbox_mm["x"]
    y = bbox_mm["y"]
    width = bbox_mm["width"]
    height = bbox_mm["height"]
    area = width * height
    aspect = width / height if height > 0 else 0.0
    y_pct = y / page_height_mm
    x_pct = x / page_width_mm

    scores = {
        "qrcode": _score_qrcode(width, height, aspect, x, y_pct),
        "logo":   _score_logo(area, y_pct, width, height),
        "map":    _score_map(area, aspect, y_pct),
        "header": _score_header(width, height, y_pct),
        "footer": _score_footer(width, y_pct),
        "line":   _score_line(width, height),
        "image":  _score_image(area, y_pct, aspect, x_pct),
    }

    sorted_types = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_type, best_score = sorted_types[0]
    second_score = sorted_types[1][1]
    margin = best_score - second_score

    if margin > 0.30:
        confidence = 0.85 + min(margin * 0.5, 0.15)
    elif margin > 0.10:
        confidence = 0.65 + margin * 1.0
    else:
        confidence = 0.50 + margin * 1.5

    flags = []
    if margin < 0.10:
        flags.append("ambiguous_class")
        second_name = sorted_types[1][0]
        flags.append(f"alt_{second_name}_{sorted_types[1][1]:.2f}")

    return {
        "type": best_type,
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "flags": flags,
    }
