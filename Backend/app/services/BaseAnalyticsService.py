from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import numpy as np

class BaseAnalyticsService(ABC):
    """
    Abstract base class for pose analytics services.
    """

    # Joint map for 13-joint input
    JOINT_MAP = {
        'nose': 0,
        'left_shoulder': 1, 'right_shoulder': 2,
        'left_elbow': 3, 'right_elbow': 4,
        'left_wrist': 5, 'right_wrist': 6,
        'left_hip': 7, 'right_hip': 8,
        'left_knee': 9, 'right_knee': 10,
        'left_ankle': 11, 'right_ankle': 12,
    }

    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    def analyze_pose(self, pose_3d: np.ndarray, pose_name: str) -> Dict:
        """
        Analyze a pose and return detailed feedback.

        Args:
            pose_3d: (13, 3) array of joint positions in world coordinates.
            pose_name: Name of the pose phase.

        Returns:
            Analysis results with measurements, errors, overall score, and bone_scores.
        """
        pass

    def _get_segment_map(self) -> Dict[Tuple[int, int], int]:
        """
        Returns a mapping from (start_joint_idx, end_joint_idx) to segment_id.
        This map is consistent with the VisualisationService.
        """
        segment_definitions = [
            (self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['left_elbow']),    # 0: L Upper Arm
            (self.JOINT_MAP['left_elbow'], self.JOINT_MAP['left_wrist']),      # 1: L Forearm
            (self.JOINT_MAP['right_shoulder'], self.JOINT_MAP['right_elbow']),  # 2: R Upper Arm
            (self.JOINT_MAP['right_elbow'], self.JOINT_MAP['right_wrist']),     # 3: R Forearm
            (self.JOINT_MAP['left_hip'], self.JOINT_MAP['left_knee']),          # 4: L Thigh
            (self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle']),        # 5: L Shin
            (self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee']),        # 6: R Thigh
            (self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle']),      # 7: R Shin
            (self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder']),# 8: Shoulder Line
            (self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])          # 9: Hip Line
        ]
        return {seg_tuple: i for i, seg_tuple in enumerate(segment_definitions)}
    
    def _calculate_bone_scores_from_criterion(self, criterion_score: float, affected_segments: List[int], current_bone_scores: Dict[int, float]) -> Dict[int, float]:
        """
        Assigns a score to specified segments based on a given criterion score.
        Segments not in affected_segments will retain their current score or default to 1.0.
        """
        # Ensure that current_bone_scores is initialized with 1.0 for all 10 segments
        initial_bone_scores = {i: 1.0 for i in range(10)}
        initial_bone_scores.update(current_bone_scores)

        for segment_id in affected_segments:
            # We take the minimum score if a segment is affected by multiple criteria
            initial_bone_scores[segment_id] = min(initial_bone_scores.get(segment_id, 1.0), criterion_score)
        return initial_bone_scores

    def aggregate_frame_feedback(self, frame_analyses: List[Dict]) -> Dict:
        """
        Aggregate feedback from multiple frames to identify consistent errors and average bone scores.

        Args:
            frame_analyses: List of analysis results from multiple frames.

        Returns:
            Aggregated feedback with most common errors and average bone scores.
        """
        error_counts = {}
        all_measurements = {}
        all_bone_scores = {i: [] for i in range(10)} # Assuming 10 segments

        for analysis in frame_analyses:
            if not analysis:
                continue
            for error in analysis.get('errors', []):
                criterion = error['criterion']
                if criterion not in error_counts:
                    error_counts[criterion] = {
                        'count': 0,
                        'example': error,
                        'frames': []
                    }
                error_counts[criterion]['count'] += 1
            
            for key, value in analysis.get('measurements', {}).items():
                if key not in all_measurements:
                    all_measurements[key] = []
                all_measurements[key].append(value)
            
            # Aggregate bone scores
            for seg_id, score in analysis.get('bone_scores', {}).items():
                all_bone_scores[seg_id].append(score)
        
        # Calculate average measurements
        avg_measurements = {
            key: np.mean(values) for key, values in all_measurements.items()
        }

        # Calculate average bone scores
        avg_bone_scores = {seg_id: np.mean(scores) for seg_id, scores in all_bone_scores.items() if scores}
        
        # Sort errors by frequency
        sorted_errors = sorted(
            error_counts.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return {
            'avg_measurements': avg_measurements,
            'common_errors': [
                {
                    **err['example'],
                    'frequency': err['count'] / len(frame_analyses) if frame_analyses else 0
                }
                for criterion, err in sorted_errors
            ],
            'avg_bone_scores': avg_bone_scores
        }

    def calculate_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        Calculate angle at p2 formed by p1-p2-p3.
        
        Args:
            p1, p2, p3: 3D points (x, y, z)
            
        Returns:
            Angle in degrees (0-180)
        """
        v1 = p1 - p2
        v2 = p3 - p2
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle = np.arccos(cos_angle)
        return np.degrees(angle)

    def calculate_distance(self, p1: np.ndarray, p2: np.ndarray) -> float:
        """Calculate Euclidean distance between two points."""
        return np.linalg.norm(p1 - p2)

    def calculate_vertical_alignment(self, points: List[np.ndarray]) -> float:
        """
        Calculate how well points align vertically.
        
        Args:
            points: List of 3D points
            
        Returns:
            Deviation from vertical (0 = perfect vertical alignment)
        """
        if len(points) < 2:
            return 0.0
        
        # Calculate center of mass
        center = np.mean(points, axis=0)
        
        # Calculate horizontal deviation from center
        deviations = []
        for point in points:
            horizontal_distance = np.sqrt(
                (point[0] - center[0])**2 + (point[2] - center[2])**2
            )
            deviations.append(horizontal_distance)
        
        return np.mean(deviations)
