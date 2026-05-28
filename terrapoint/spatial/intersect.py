from shapely.geometry import shape


def filter_by_intersection(features: list[dict], parcel_geometry: dict) -> list[dict]:
    """Filter WFS features to only those intersecting the parcel polygon.
    Uses Shapely for precise server-side polygon intersection.
    """
    parcel_geom = shape(parcel_geometry)
    result = []
    for feature in features:
        try:
            feat_geom = shape(feature.get("geometry", {}))
            if feat_geom.is_valid and feat_geom.intersects(parcel_geom):
                result.append(feature)
        except Exception:
            continue
    return result
