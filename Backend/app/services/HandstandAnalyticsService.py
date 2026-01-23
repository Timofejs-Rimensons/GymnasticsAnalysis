import numpy as np
from typing import Dict, List
from services.BaseAnalyticsService import BaseAnalyticsService

class HandstandAnalyticsService(BaseAnalyticsService):
    """
    Analyzes pose geometry and provides actionable feedback.
    Uses 3D world coordinates from MediaPipe.
    
    Joint indices:
    0: nose, 1-2: shoulders, 3-4: elbows, 5-6: wrists,
    7-8: hips, 9-10: knees, 11-12: ankles
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: Pose criteria from config.json
        """
        self.config = config
        
    # ============================================================
    # Geometric Calculations
    # ============================================================
    
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
    
    def calculate_distance(self, p1: np.ndarray, p2: np.ndarray) -> float:
        """Calculate Euclidean distance between two points."""
        return np.linalg.norm(p1 - p2)
    
    def calculate_straightness(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        Calculate how straight three points are (180° = perfectly straight).
        
        Returns:
            Deviation from 180° (0 = perfectly straight)
        """
        angle = self.calculate_angle(p1, p2, p3)
        return abs(180 - angle)
    
    # ============================================================
    # Pose-Specific Analysis
    # ============================================================
    
    def analyze_starting_position(self, pose_3d: np.ndarray) -> Dict:
        """
        Analyze starting position criteria:
        1. Arms up (shoulder-elbow angle with vertical)
        2. Big step (distance between feet)
        3. Back leg straight (hip-knee-ankle angle)
        
        Args:
            pose_3d: (13, 3) array of joint positions
            
        Returns:
            Dictionary with measurements and feedback
        """
        criteria = self.config.get('Starting', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0  # Start with perfect score
        }
        
        # 1. Arms up - check if arms are raised vertically
        left_shoulder, left_elbow = pose_3d[1], pose_3d[3]
        right_shoulder, right_elbow = pose_3d[2], pose_3d[4]
        
        # Create vertical reference point above shoulder
        left_vertical = left_shoulder.copy()
        left_vertical[1] += 1.0  # 1 meter up
        
        left_arm_angle = self.calculate_angle(left_vertical, left_shoulder, left_elbow)
        
        feedback['measurements']['left_arm_angle'] = left_arm_angle
        
        if 'arms_vertical_angle' in criteria:
            threshold = criteria['arms_vertical_angle']
            if left_arm_angle < threshold.get('min', 0) or left_arm_angle > threshold.get('max', 180):
                deviation = min(abs(left_arm_angle - threshold['min']), 
                               abs(left_arm_angle - threshold['max']))
                
                if left_arm_angle < threshold.get('min', 0):
                    improvement_msg = 'Raise your arms higher overhead'
                else:
                    improvement_msg = 'Bring your arms more upright and closer to vertical'
                
                feedback['errors'].append({
                    'criterion': 'arms_vertical_angle',
                    'severity': 'high' if deviation > 30 else 'medium' if deviation > 15 else 'low',
                    'measurement': f"{left_arm_angle:.1f}° from vertical",
                    'improvement': threshold.get('tip', improvement_msg)
                })
                feedback['score'] -= 0.3
        
        # 2. Back leg straight - knee angle should be ~180°
        right_hip, right_knee, right_ankle = pose_3d[8], pose_3d[10], pose_3d[12]
        back_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        
        feedback['measurements']['back_knee_angle'] = back_knee_angle
        
        if 'back_leg_knee_angle' in criteria:
            threshold = criteria['back_leg_knee_angle']
            if back_knee_angle < threshold.get('min', 0):
                deviation = threshold['min'] - back_knee_angle
                feedback['errors'].append({
                    'criterion': 'back_leg_straight',
                    'severity': 'high' if deviation > 30 else 'medium' if deviation > 15 else 'low',
                    'measurement': f"Knee bent at {back_knee_angle:.1f}° (should be ~180°)",
                    'improvement': threshold.get('tip', 'Keep your back leg fully extended and straight')
                })
                feedback['score'] -= 0.35
        
        # 3. Step distance
        left_ankle, right_ankle = pose_3d[11], pose_3d[12]
        step_distance = self.calculate_distance(left_ankle, right_ankle)
        
        feedback['measurements']['step_distance'] = step_distance
        
        if 'step_distance' in criteria:
            threshold = criteria['step_distance']
            if step_distance < threshold.get('min', 0) or step_distance > threshold.get('max', 10):
                if step_distance < threshold.get('min', 0):
                    improvement_msg = 'Take a bigger step forward to build momentum'
                else:
                    improvement_msg = 'Reduce your step size for better control'
                
                feedback['errors'].append({
                    'criterion': 'step_distance',
                    'severity': 'medium',
                    'measurement': f"{step_distance:.2f}m step distance",
                    'improvement': threshold.get('tip', improvement_msg)
                })
                feedback['score'] -= 0.2
        
        feedback['score'] = max(0.0, feedback['score'])
        return feedback
    
    def analyze_swing(self, pose_3d: np.ndarray) -> Dict:
        """
        Analyze swing criteria:
        1. Back leg straight (hip-knee-ankle angle ~180°)
        2. Forward lean (torso angle)
        
        Args:
            pose_3d: (13, 3) array of joint positions
            
        Returns:
            Dictionary with measurements and feedback
        """
        criteria = self.config.get('Swing', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0
        }
        
        # 1. Back leg straight
        right_hip, right_knee, right_ankle = pose_3d[8], pose_3d[10], pose_3d[12]
        back_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        
        feedback['measurements']['back_knee_angle'] = back_knee_angle
        
        if 'back_leg_knee_angle' in criteria:
            threshold = criteria['back_leg_knee_angle']
            if back_knee_angle < threshold.get('min', 170):
                deviation = threshold['min'] - back_knee_angle
                feedback['errors'].append({
                    'criterion': 'back_leg_straight',
                    'severity': 'high' if deviation > 30 else 'medium' if deviation > 15 else 'low',
                    'measurement': f"Knee bent at {back_knee_angle:.1f}°",
                    'improvement': threshold.get('tip', 'Maintain a fully extended back leg throughout the swing')
                })
                feedback['score'] -= 0.5
        
        feedback['score'] = max(0.0, feedback['score'])
        return feedback
    
    def analyze_handstand(self, pose_3d: np.ndarray) -> Dict:
        """
        Analyze handstand criteria:
        1. Legs aligned vertically (ankle-hip-shoulder alignment)
        2. Back straight (shoulder-hip-ankle angle ~180°)
        3. Hands aligned (shoulder width)
        4. Shoulders over arms (shoulder-elbow-wrist vertical)
        
        Args:
            pose_3d: (13, 3) array of joint positions
            
        Returns:
            Dictionary with measurements and feedback
        """
        criteria = self.config.get('Handstand', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0
        }
        
        # Average left/right joints for symmetry
        shoulder = (pose_3d[1] + pose_3d[2]) / 2
        hip = (pose_3d[7] + pose_3d[8]) / 2
        ankle = (pose_3d[11] + pose_3d[12]) / 2
        wrist = (pose_3d[5] + pose_3d[6]) / 2
        
        # 1. Leg alignment - check if ankle, hip, shoulder are vertically aligned
        leg_alignment_deviation = self.calculate_vertical_alignment([ankle, hip, shoulder])
        
        feedback['measurements']['leg_alignment_deviation'] = leg_alignment_deviation
        
        if 'leg_alignment_deviation' in criteria:
            threshold = criteria['leg_alignment_deviation']
            if leg_alignment_deviation > threshold.get('max', 0.15):
                feedback['errors'].append({
                    'criterion': 'leg_alignment',
                    'severity': 'high' if leg_alignment_deviation > 0.3 else 'medium',
                    'measurement': f"{leg_alignment_deviation:.2f}m deviation from vertical",
                    'improvement': threshold.get('tip', 'Stack your hips and legs directly over your shoulders')
                })
                feedback['score'] -= 0.3
        
        # 2. Back straightness - shoulder-hip-ankle should be ~180°
        back_angle = self.calculate_angle(shoulder, hip, ankle)
        back_straightness = abs(180 - back_angle)
        
        feedback['measurements']['back_straightness'] = back_straightness
        
        if 'back_straightness' in criteria:
            threshold = criteria['back_straightness']
            if back_straightness > threshold.get('max', 10):
                # Determine if back is arched or piked
                if back_angle < 180:
                    improvement_msg = 'Avoid arching your back - tighten your core and glutes'
                else:
                    improvement_msg = 'Avoid piking at the hips - push your shoulders forward slightly'
                
                feedback['errors'].append({
                    'criterion': 'back_straightness',
                    'severity': 'medium' if back_straightness < 20 else 'high',
                    'measurement': f"{back_straightness:.1f}° deviation from straight",
                    'improvement': threshold.get('tip', improvement_msg)
                })
                feedback['score'] -= 0.25
        
        # 3. Hand width - should match shoulder width
        left_wrist, right_wrist = pose_3d[5], pose_3d[6]
        left_shoulder, right_shoulder = pose_3d[1], pose_3d[2]
        
        hand_width = self.calculate_distance(left_wrist, right_wrist)
        shoulder_width = self.calculate_distance(left_shoulder, right_shoulder)
        
        hand_width_ratio = hand_width / shoulder_width if shoulder_width > 0 else 0
        
        feedback['measurements']['hand_width_ratio'] = hand_width_ratio
        
        if 'hand_width_ratio' in criteria:
            threshold = criteria['hand_width_ratio']
            if hand_width_ratio < threshold.get('min', 0.9) or hand_width_ratio > threshold.get('max', 1.3):
                if hand_width_ratio < threshold.get('min', 0.9):
                    improvement_msg = 'Place your hands wider apart to match shoulder width'
                else:
                    improvement_msg = 'Bring your hands closer together to match shoulder width'
                
                feedback['errors'].append({
                    'criterion': 'hand_placement',
                    'severity': 'low',
                    'measurement': f"Hand width is {hand_width_ratio:.1f}x shoulder width",
                    'improvement': threshold.get('tip', improvement_msg)
                })
                feedback['score'] -= 0.15
        
        # 4. Shoulders over arms - check vertical alignment
        elbow = (pose_3d[3] + pose_3d[4]) / 2
        shoulder_arm_alignment = self.calculate_vertical_alignment([wrist, elbow, shoulder])
        
        feedback['measurements']['shoulder_arm_alignment'] = shoulder_arm_alignment
        
        if 'shoulder_arm_alignment' in criteria:
            threshold = criteria['shoulder_arm_alignment']
            if shoulder_arm_alignment > threshold.get('max', 0.1):
                feedback['errors'].append({
                    'criterion': 'shoulder_position',
                    'severity': 'medium',
                    'measurement': f"{shoulder_arm_alignment:.2f}m deviation",
                    'improvement': threshold.get('tip', 'Push your shoulders forward to align directly over your wrists')
                })
                feedback['score'] -= 0.2
        
        feedback['score'] = max(0.0, feedback['score'])
        return feedback
    
    def analyze_landing(self, pose_3d: np.ndarray) -> Dict:
        """
        Analyze landing criteria (define based on client requirements).
        
        Args:
            pose_3d: (13, 3) array of joint positions
            
        Returns:
            Dictionary with measurements and feedback
        """
        criteria = self.config.get('Landing', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0
        }
        
        # Landing-specific criteria: knee flexion
        left_hip, left_knee, left_ankle = pose_3d[7], pose_3d[9], pose_3d[11]
        right_hip, right_knee, right_ankle = pose_3d[8], pose_3d[10], pose_3d[12]
        
        left_knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
        
        feedback['measurements']['avg_knee_flexion'] = avg_knee_angle
        
        if 'knee_flexion' in criteria:
            threshold = criteria['knee_flexion']
            if avg_knee_angle < threshold.get('min', 90) or avg_knee_angle > threshold.get('max', 140):
                if avg_knee_angle < threshold.get('min', 90):
                    improvement_msg = 'Bend your knees more to properly absorb the landing impact'
                else:
                    improvement_msg = 'Land with less knee bend for a more controlled finish'
                
                feedback['errors'].append({
                    'criterion': 'knee_flexion',
                    'severity': 'medium',
                    'measurement': f"Knee angle at {avg_knee_angle:.1f}°",
                    'improvement': threshold.get('tip', improvement_msg)
                })
                feedback['score'] -= 0.3
        
        feedback['score'] = max(0.0, feedback['score'])
        return feedback
    
    # ============================================================
    # Main Analysis Method
    # ============================================================
    
    def analyze_pose(self, pose_3d: np.ndarray, pose_name: str) -> Dict:
        """
        Analyze a pose and return detailed feedback.
        
        Args:
            pose_3d: (13, 3) array of joint positions
            pose_name: Name of the pose phase
            
        Returns:
            Analysis results with measurements and feedback
        """
        if pose_name == 'Starting':
            return self.analyze_starting_position(pose_3d)
        elif pose_name == 'Swing':
            return self.analyze_swing(pose_3d)
        elif pose_name == 'Handstand':
            return self.analyze_handstand(pose_3d)
        elif pose_name == 'Landing':
            return self.analyze_landing(pose_3d)
        else:
            return {
                'measurements': {},
                'errors': [],
                'score': 0.0
            }
    
    def aggregate_frame_feedback(self, frame_analyses: List[Dict]) -> Dict:
        """
        Aggregate feedback from multiple frames to identify consistent errors.
        
        Args:
            frame_analyses: List of analysis results from multiple frames
            
        Returns:
            Aggregated feedback with most common errors
        """
        error_counts = {}
        all_measurements = {}
        
        for analysis in frame_analyses:
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
        
        # Calculate average measurements
        avg_measurements = {
            key: np.mean(values) for key, values in all_measurements.items()
        }
        
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
            ]
        }
