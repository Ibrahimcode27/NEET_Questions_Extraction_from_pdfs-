def compute_centroid(vertices):
    xs = [x for x, y in vertices]
    ys = [y for x, y in vertices]
    return (sum(xs) / len(xs), sum(ys) / len(ys))

def is_point_inside_box(point, box):
    x, y = point
    return box["x_min"] <= x <= box["x_max"] and box["y_min"] <= y <= box["y_max"]

def merge_texts_in_box(detections, box):
    texts = []
    for detection in detections:
        # detection should be a dict with "text" and "vertices"
        if not isinstance(detection, dict):
            continue
        if "vertices" not in detection or "text" not in detection:
            continue
        centroid = compute_centroid(detection["vertices"])
        if is_point_inside_box(centroid, box):
            texts.append(detection["text"])
    return " ".join(texts)

def map_linked_question_text_to_diagram(diagram_links, ocr_data):
    mapping = {}
    for link in diagram_links:
        if link.get("linked_diagram") and "q_box" in link:
            page = link.get("page")
            data = ocr_data.get(page)
            if not data:
                continue
            if isinstance(data, tuple):
                detections = data[1]
            else:
                detections = data
            if not detections:
                continue
            box = link["q_box"]
            question_text = merge_texts_in_box(detections, box)
            if question_text:
                mapping[question_text] = link["linked_diagram"]
    return mapping
