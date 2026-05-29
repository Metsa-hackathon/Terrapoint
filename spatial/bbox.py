from shapely.geometry import shape


def calculate_bbox(geometry: dict, buffer_deg: float = 0.005) -> tuple[float, float, float, float]:
    geom = shape(geometry)
    minx, miny, maxx, maxy = geom.bounds
    return (minx - buffer_deg, miny - buffer_deg, maxx + buffer_deg, maxy + buffer_deg)


def bbox_to_wfs_string(bbox: tuple[float, float, float, float]) -> str:
    return f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
