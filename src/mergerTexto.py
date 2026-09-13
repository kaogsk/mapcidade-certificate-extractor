Y_MERGE_THRESHOLD_MM = 2.0
X_GAP_THRESHOLD_MM = 8.0
FONT_SIZE_TOLERANCE_PT = 0.5


def should_merge_blocks(a: dict, b: dict) -> bool:
    """True se dois itens de texto (nível bloco) devem ser mesclados por proximidade."""
    if a["page"] != b["page"]:
        return False

    bb_a = a["bounding_box_mm"]
    bb_b = b["bounding_box_mm"]

    # Vertical check: compute gap between the two vertical ranges
    # a spans [a_y0, a_y1], b spans [b_y0, b_y1]
    a_y0 = a.get("_y0_mm", bb_a["y"] - bb_a["height"])
    a_y1 = bb_a["y"]
    b_y0 = b.get("_y0_mm", bb_b["y"] - bb_b["height"])
    b_y1 = bb_b["y"]

    # If ranges overlap, dy = 0; otherwise gap between them
    if a_y1 >= b_y0 and b_y1 >= a_y0:
        dy = 0.0
    else:
        dy = max(b_y0 - a_y1, a_y0 - b_y1)

    if dy > Y_MERGE_THRESHOLD_MM:
        return False

    x_end_a = bb_a["x"] + bb_a["width"]
    dx = bb_b["x"] - x_end_a
    if dx < 0:
        dx = 0.0
    if dx > X_GAP_THRESHOLD_MM:
        return False

    font_a = a.get("font", {})
    font_b = b.get("font", {})
    if font_a.get("name") and font_b.get("name"):
        if font_a["name"] != font_b["name"]:
            return False
    if font_a.get("size_pt") and font_b.get("size_pt"):
        if abs(font_a["size_pt"] - font_b["size_pt"]) > FONT_SIZE_TOLERANCE_PT:
            return False

    return True


def _group_plumber_words_by_line(words: list, y_tolerance_mm: float = 1.5) -> list:
    """Agrupa words do pdfplumber em linhas por proximidade de y0."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w["page"], w["y0"], w["x0"]))
    lines = []
    current_line = [sorted_words[0]]
    for word in sorted_words[1:]:
        prev = current_line[-1]
        if word["page"] == prev["page"] and abs(word["y0"] - prev["y0"]) <= y_tolerance_mm:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
    lines.append(current_line)
    return lines


def _plumber_line_overlaps_item(plumber_line: list, item: dict) -> bool:
    """True se uma linha do pdfplumber sobrepõe o bounding box do item."""
    if not plumber_line:
        return False
    line_page = plumber_line[0]["page"]
    if line_page != item["page"]:
        return False
    bb = item["bounding_box_mm"]
    item_x0 = bb["x"]
    item_x1 = bb["x"] + bb["width"]
    item_y0 = item.get("_y0_mm", bb["y"] - bb["height"])
    item_y1 = bb["y"]
    for word in plumber_line:
        if word["x0"] < item_x1 and word["x1"] > item_x0:
            if word["y0"] < item_y1 and word["y1"] > item_y0:
                return True
    return False


def _words_inside_item(item: dict, words: list) -> list:
    """Retorna words do pdfplumber contidos (ou sobrepostos) ao bbox do item."""
    bb = item["bounding_box_mm"]
    item_x0 = bb["x"]
    item_x1 = bb["x"] + bb["width"]
    item_y0 = item.get("_y0_mm", bb["y"] - bb["height"])
    item_y1 = bb["y"]
    inside = []
    for word in words:
        if word.get("page") != item["page"]:
            continue
        if word["x0"] < item_x1 and word["x1"] > item_x0:
            if word["y0"] < item_y1 and word["y1"] > item_y0:
                inside.append(word)
    return inside


def _check_split_conflict(item: dict, plumber_lines: list) -> bool:
    """True se pdfplumber detecta múltiplas linhas dentro de um único bloco pymupdf,
    ou se há múltiplas palavras distintas dentro do bloco."""
    overlapping = [ln for ln in plumber_lines if _plumber_line_overlaps_item(ln, item)]
    if len(overlapping) > 1:
        return True
    # Also flag when a single pymupdf block contains 2+ pdfplumber words
    # (potential over-merging by pymupdf)
    if len(overlapping) == 1 and len(overlapping[0]) >= 2:
        return True
    return False


def _merge_two(a: dict, b: dict, confidence: float, flags: list) -> dict:
    """Mescla dois itens em um, expandindo bbox e concatenando texto."""
    bb_a = a["bounding_box_mm"]
    bb_b = b["bounding_box_mm"]
    x0 = min(bb_a["x"], bb_b["x"])
    y0 = min(
        a.get("_y0_mm", bb_a["y"] - bb_a["height"]),
        b.get("_y0_mm", bb_b["y"] - bb_b["height"]),
    )
    x1 = max(bb_a["x"] + bb_a["width"], bb_b["x"] + bb_b["width"])
    y1 = max(bb_a["y"], bb_b["y"])

    sep = "\n" if abs(bb_b["x"] - (bb_a["x"] + bb_a["width"])) > 2.0 else " "
    merged_text = a["text"] + sep + b["text"]

    merged_flags = list(set(a.get("confidence_flags", []) + b.get("confidence_flags", []) + flags))

    return {
        "type": "text",
        "page": a["page"],
        "text": merged_text,
        "bounding_box_mm": {
            "x": round(x0, 2),
            "y": round(y1, 2),
            "width": round(x1 - x0, 2),
            "height": round(y1 - y0, 2),
        },
        "_y0_mm": round(y0, 2),
        "font": a.get("font", {}),
        "confidence": round(confidence, 3),
        "confidence_flags": merged_flags,
    }


def merge_text_items(items: list, pdfplumber_words: list) -> list:
    """
    Mescla itens de texto por proximidade com validação cruzada pdfplumber.

    items: itens nível-bloco de processarPdf (cada um com _y0_mm)
    pdfplumber_words: palavras do pdfplumber com x0,y0,x1,y1,page (em mm)
    """
    plumber_lines = _group_plumber_words_by_line(pdfplumber_words)

    processed = []
    for item in items:
        item = dict(item)
        if _check_split_conflict(item, plumber_lines):
            item["confidence"] = min(item.get("confidence", 0.95), 0.65)
            flags = list(item.get("confidence_flags", []))
            if "split_conflict" not in flags:
                flags.append("split_conflict")
            item["confidence_flags"] = flags
        processed.append(item)

    if not processed:
        return []

    result = [processed[0]]
    for current in processed[1:]:
        last = result[-1]
        if should_merge_blocks(last, current):
            last_in_same_plumber_line = any(
                _plumber_line_overlaps_item(ln, last) and _plumber_line_overlaps_item(ln, current)
                for ln in plumber_lines
            )
            if last_in_same_plumber_line:
                confidence = 0.90
                flags = ["merged_cross"]
            else:
                confidence = 0.85
                flags = ["merged_proximity"]

            merged = _merge_two(last, current, confidence, flags)
            result[-1] = merged
        else:
            result.append(current)

    return result
