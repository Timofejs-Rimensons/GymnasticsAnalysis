import numpy as np
from typing import Dict

def get_lanmark_coord(landmarks: Dict, landmark_index: int) -> Dict[str, float]:
    """
    Get coordinates for a specific landmark
    
    Args:
        landmarks: Dictionary containing all landmarks
        landmark_index: MediaPipe landmark index (0-32)
    
    Returns:
        Dictionary with x, y, z coordinates
    """
    landmark_key = f"landmark_{landmark_index}"
    if landmark_key in landmarks:
        return landmarks[landmark_key]
    return {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.0}

def calculate_angle(point1: Dict, point2: Dict, point3: Dict) -> float:
    """
    Calculate angle between three points (in degrees)

    Args:
        point1: First point (dict with 'x', 'y', 'z' keys)
        point2: Vertex point (dict with 'x', 'y', 'z' keys)
        point3: Third point (dict with 'x', 'y', 'z' keys)

    Returns:
        Angle in degrees (0-180), or 0.0 if calculation fails
    """
    try:
        a = np.array((point1['x'], point1['y'], point1['z']))
        b = np.array((point2['x'], point2['y'], point2['z']))
        c = np.array((point3['x'], point3['y'], point3['z']))

        ba = b - a
        bc = c - b

        # Check for zero vectors (would cause division by zero)
        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)

        if norm_ba == 0 or norm_bc == 0:
            return 0.0

        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

        result = np.degrees(angle)

        # Return 0 if result is NaN or infinite
        if np.isnan(result) or np.isinf(result):
            return 0.0

        return result
    except Exception:
        return 0.0

def calculate_distance(point1: Dict, point2: Dict) -> float:
    """
    Calculate Euclidean distance between two points

    Returns:
        Distance between points, or 0.0 if calculation fails
    """
    try:
        p1 = np.array([point1['x'], point1['y'], point1['z']])
        p2 = np.array([point2['x'], point2['y'], point2['z']])
        distance = np.linalg.norm(p1 - p2)

        # Return 0 if result is NaN or infinite
        if np.isnan(distance) or np.isinf(distance):
            return 0.0

        return distance
    except Exception:
        return 0.0

def calculate_vertical_angle(shoulder: Dict, hip: Dict, ankle: Dict) -> float:
    """
    Calculate how vertical the body is (0° = horizontal, 90° = vertical)
    """
    # This is a simplified calculation
    # You can make it more sophisticated based on your needs
    return calculate_angle(shoulder, hip, ankle)