from shapely.geometry import shape


def calculate_bbox(geometry: dict) -> tuple[float, float, float, float]:
    """Calculate bounding box from GeoJSON geometry.
    Returns (minx, miny, maxx, maxy) in EPSG:4326.
    """
    geom = shape(geometry)
    return geom.bounds


def bbox_to_wfs_string(bbox: tuple[float, float, float, float]) -> str:
    """Convert bbox tuple to WFS BBOX parameter string."""
    minx, miny, maxx, maxy = bbox
    return f"{minx},{miny},{maxx},{maxy},EPSG:4326"
