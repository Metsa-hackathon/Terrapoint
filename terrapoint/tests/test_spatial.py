import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spatial.bbox import calculate_bbox, bbox_to_wfs_string
from spatial.intersect import filter_by_intersection


def test_calculate_bbox():
    geom = {
        "type": "Polygon",
        "coordinates": [[[24.5, 59.3], [25.0, 59.3], [25.0, 59.5], [24.5, 59.5], [24.5, 59.3]]]
    }
    bbox = calculate_bbox(geom)
    assert len(bbox) == 4
    assert bbox[0] == 24.5
    assert bbox[1] == 59.3
    assert bbox[2] == 25.0
    assert bbox[3] == 59.5


def test_bbox_to_wfs_string():
    bbox = (24.5, 59.3, 25.0, 59.5)
    result = bbox_to_wfs_string(bbox)
    assert result == "24.5,59.3,25.0,59.5,EPSG:4326"


def test_filter_by_intersection():
    parcel = {
        "type": "Polygon",
        "coordinates": [[[24.5, 59.3], [25.0, 59.3], [25.0, 59.5], [24.5, 59.5], [24.5, 59.3]]]
    }
    features = [
        {"geometry": {"type": "Polygon", "coordinates": [[[24.6, 59.35], [24.8, 59.35], [24.8, 59.45], [24.6, 59.45], [24.6, 59.35]]]}},
        {"geometry": {"type": "Polygon", "coordinates": [[[26.0, 60.0], [26.5, 60.0], [26.5, 60.5], [26.0, 60.5], [26.0, 60.0]]]}},
    ]
    result = filter_by_intersection(features, parcel)
    assert len(result) == 1


if __name__ == "__main__":
    test_calculate_bbox()
    test_bbox_to_wfs_string()
    test_filter_by_intersection()
    print("All spatial tests passed!")
