import numpy as np
from typing import Optional, Tuple
from ultralytics import YOLO

class BoxDetectionService:
    """
    Service for detecting vault box in gymnastics videos using YOLO.
    Provides box edge coordinates for hand placement analysis.
    """

    def __init__(self, model_path: str = "best.pt"):
        """
        Initialize the box detection service.

        Args:
            model_path: Path to the YOLO model weights
        """
        self.model = YOLO(model_path)

    def detect_box_edge(self, frame: np.ndarray) -> Optional[float]:
        """
        Detect the vault box in a frame and return the x-coordinate of its edge.

        Args:
            frame: Video frame as numpy array (H, W, C)

        Returns:
            X-coordinate of the box edge (right edge of the box), or None if not detected
        """
        # Run YOLO detection
        results = self.model(frame, verbose=False)

        if len(results) == 0 or len(results[0].boxes) == 0:
            return None

        # Get the box with highest confidence
        boxes = results[0].boxes
        confidences = boxes.conf.cpu().numpy()

        if len(confidences) == 0:
            return None

        best_box_idx = np.argmax(confidences)
        box = boxes.xyxy[best_box_idx].cpu().numpy()  # [x1, y1, x2, y2]

        # Return the right edge x-coordinate (x2)
        # This is where hands should be placed during the vault
        box_edge_x = float(box[2])

        return box_edge_x

    def detect_box_edge_normalized(self, frame: np.ndarray) -> Optional[float]:
        """
        Detect the vault box and return normalized x-coordinate (0-1 range).

        Args:
            frame: Video frame as numpy array (H, W, C)

        Returns:
            Normalized x-coordinate of the box edge, or None if not detected
        """
        box_edge_x = self.detect_box_edge(frame)

        if box_edge_x is None:
            return None

        # Normalize by frame width
        frame_width = frame.shape[1]
        return box_edge_x / frame_width if frame_width > 0 else None

    def get_box_bounding_box(self, frame: np.ndarray) -> Optional[Tuple[float, float, float, float]]:
        """
        Get the full bounding box of the detected vault box.

        Args:
            frame: Video frame as numpy array (H, W, C)

        Returns:
            Tuple of (x1, y1, x2, y2) coordinates, or None if not detected
        """
        results = self.model(frame, verbose=False)

        if len(results) == 0 or len(results[0].boxes) == 0:
            return None

        boxes = results[0].boxes
        confidences = boxes.conf.cpu().numpy()

        if len(confidences) == 0:
            return None

        best_box_idx = np.argmax(confidences)
        box = boxes.xyxy[best_box_idx].cpu().numpy()

        return tuple(box)
