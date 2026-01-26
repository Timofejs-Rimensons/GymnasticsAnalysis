# import numpy as np
# from typing import Dict
# from services.BaseAnalyticsService import BaseAnalyticsService

# class LeapAnalyticsService(BaseAnalyticsService):
#     """
#     Analyzes pose geometry for a leap and provides actionable feedback.
#     Uses 3D world coordinates from MediaPipe (13 joints).
#     """

#     def analyze_pose(self, pose_3d: np.ndarray, pose_name: str) -> Dict:
#         """
#         Analyze a pose and return detailed feedback.
#         This is a stub implementation for the leap.
#         """
#         pose_analyzer = getattr(self, f"analyze_{pose_name.lower().replace(' ', '_')}", None)
#         if pose_analyzer:
#             return pose_analyzer(pose_3d)
        
#         return {
#             'measurements': {},
#             'errors': [],
#             'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)} # Default perfect score for all bones
#         }

#     def analyze_runup(self, pose_3d: np.ndarray) -> Dict:
#         # Stub: Add analysis for runup phase
#         return {
#             'measurements': {}, 'errors': [], 'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)}
#         }

#     def analyze_takeoff(self, pose_3d: np.ndarray) -> Dict:
#         # Stub: Add analysis for takeoff phase
#         return {
#             'measurements': {}, 'errors': [], 'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)}
#         }

#     def analyze_handplacement(self, pose_3d: np.ndarray) -> Dict:
#         # Stub: Add analysis for handplacement phase
#         return {
#             'measurements': {}, 'errors': [], 'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)}
#         }

#     def analyze_flight_down(self, pose_3d: np.ndarray) -> Dict:
#         # Stub: Add analysis for flight_down phase
#         return {
#             'measurements': {}, 'errors': [], 'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)}
#         }

#     def analyze_landing(self, pose_3d: np.ndarray) -> Dict:
#         # Stub: Add analysis for landing phase
#         return {
#             'measurements': {}, 'errors': [], 'score': 1.0,
#             'segment_scores': {i: 1.0 for i in range(10)}
#         }

import numpy as np
from typing import Dict, List
from services.BaseAnalyticsService import BaseAnalyticsService

class LeapAnalyticsService(BaseAnalyticsService):
    """
    Analyzes pose geometry for a straddle jump and provides actionable feedback.
    Uses 3D world coordinates from MediaPipe (13 joints) and vault box detection from best.pt.
    """

    def analyze_pose(self, pose_3d: np.ndarray, pose_name: str, box_edge_x: float = None) -> Dict:
        """
        Analyze a pose and return detailed feedback.

        Args:
            pose_3d: (13, 3) array of joint positions
            pose_name: Name of the pose phase
            box_edge_x: Optional X-coordinate of the vault box edge (for hand placement validation)

        Returns:
            Analysis results with measurements, errors, overall score, and bone_scores.
        """
        if pose_name == 'Run-up':
            return self.analyze_run_up(pose_3d)
        elif pose_name == 'Take-off':
            return self.analyze_take_off(pose_3d)
        elif pose_name == 'Flight1':
            return self.analyze_flight1(pose_3d, box_edge_x)
        elif pose_name == 'Flight2':
            return self.analyze_flight2(pose_3d)
        elif pose_name == 'Landing':
            return self.analyze_landing(pose_3d)
        else:
            return {
                'measurements': {},
                'errors': [],
                'score': 1.0,
                'bone_scores': {i: 1.0 for i in range(10)}
            }

    def analyze_run_up(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Run-up', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0,
            'bone_scores': {i: 1.0 for i in range(10)}
        }

        segment_map = self._get_segment_map()

        # 1. Torso upright
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        right_shoulder = pose_3d[self.JOINT_MAP['right_shoulder']]
        right_hip = pose_3d[self.JOINT_MAP['right_hip']]

        torso_angle = self.calculate_angle(left_hip, left_shoulder, right_shoulder)
        feedback['measurements']['torso_angle'] = torso_angle

        if 'torso_upright' in criteria:
            threshold = criteria['torso_upright']
            min_angle = threshold.get('min', 170)
            max_angle = threshold.get('max', 190)

            torso_bone_score = 1.0
            if not (min_angle <= torso_angle <= max_angle):
                deviation = min(abs(torso_angle - min_angle), abs(torso_angle - max_angle))
                if deviation > 20:
                    torso_bone_score = 0.0
                elif deviation > 10:
                    torso_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'torso_upright',
                    'improvement': threshold.get('tip', 'Keep your torso upright during the run-up.'),
                    'measurement': f'{torso_angle:.1f}° (target: {min_angle}-{max_angle}°)',
                    'severity': 'high' if deviation > 20 else 'medium'
                })
                feedback['score'] -= 0.2

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                torso_bone_score,
                [segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder'])],  # Shoulder Line
                 segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])]],  # Hip Line
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_take_off(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Take-off', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0,
            'bone_scores': {i: 1.0 for i in range(10)}
        }

        segment_map = self._get_segment_map()

        # 1. Both feet together on the springboard
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]
        feet_distance = self.calculate_distance(left_ankle, right_ankle)
        feedback['measurements']['feet_distance'] = feet_distance

        if 'feet_together' in criteria:
            threshold = criteria['feet_together']
            max_distance = threshold.get('max', 0.2)

            feet_bone_score = 1.0
            if feet_distance > max_distance:
                if feet_distance > 0.4:
                    feet_bone_score = 0.0
                elif feet_distance > 0.3:
                    feet_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'feet_together',
                    'improvement': threshold.get('tip', 'Keep both feet together on the springboard.'),
                    'measurement': f'{feet_distance:.3f}m apart (max: {max_distance}m)',
                    'severity': 'high' if feet_distance > 0.4 else 'medium'
                })
                feedback['score'] -= 0.3

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                feet_bone_score,
                [segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],
                feedback['bone_scores']
            )

        # 2. Torso upright
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        torso_angle = self.calculate_angle(left_hip, left_shoulder, pose_3d[self.JOINT_MAP['right_shoulder']])
        feedback['measurements']['torso_angle'] = torso_angle

        if 'torso_upright' in criteria:
            threshold = criteria['torso_upright']
            min_angle = threshold.get('min', 170)
            max_angle = threshold.get('max', 190)

            torso_bone_score = 1.0
            if not (min_angle <= torso_angle <= max_angle):
                deviation = min(abs(torso_angle - min_angle), abs(torso_angle - max_angle))
                if deviation > 20:
                    torso_bone_score = 0.0
                elif deviation > 10:
                    torso_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'torso_upright',
                    'improvement': threshold.get('tip', 'Keep your torso upright during take-off.'),
                    'measurement': f'{torso_angle:.1f}° (target: {min_angle}-{max_angle}°)',
                    'severity': 'high' if deviation > 20 else 'medium'
                })
                feedback['score'] -= 0.2

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                torso_bone_score,
                [segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder'])],  # Shoulder Line
                 segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])]],  # Hip Line
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_flight1(self, pose_3d: np.ndarray, box_edge_x: float) -> Dict:
        criteria = self.config.get('Flight1', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0,
            'bone_scores': {i: 1.0 for i in range(10)}
        }

        segment_map = self._get_segment_map()

        # 1. Body fully extended, feet higher than the hips
        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        extension = left_ankle[1] - left_hip[1]
        feedback['measurements']['leg_extension'] = extension

        if 'body_extended' in criteria:
            threshold = criteria['body_extended']
            min_extension = threshold.get('min', 0.3)

            extension_bone_score = 1.0
            if extension < min_extension:
                if extension < 0.1:
                    extension_bone_score = 0.0
                elif extension < 0.2:
                    extension_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'body_extended',
                    'improvement': threshold.get('tip', 'Fully extend your body, feet higher than hips.'),
                    'measurement': f'{extension:.3f}m extension (min: {min_extension}m)',
                    'severity': 'high' if extension < 0.1 else 'medium'
                })
                feedback['score'] -= 0.3

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                extension_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['left_knee'])],
                 segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],
                 segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],
                feedback['bone_scores']
            )

        # 2. Hand placement - critical for vault technique (hands must be near box edge)
        if 'hand_placement' in criteria:
            left_wrist = pose_3d[self.JOINT_MAP['left_wrist']]
            right_wrist = pose_3d[self.JOINT_MAP['right_wrist']]
            avg_hand_x = (left_wrist[0] + right_wrist[0]) / 2

            threshold = criteria['hand_placement']

            if box_edge_x is not None:
                # Box detected - measure hand placement accuracy
                hand_placement_deviation = abs(avg_hand_x - box_edge_x)
                feedback['measurements']['hand_placement_deviation'] = hand_placement_deviation

                max_deviation = threshold.get('max', 0.1)
                hand_bone_score = 1.0

                if hand_placement_deviation > max_deviation:
                    if hand_placement_deviation > 0.2:
                        hand_bone_score = 0.0
                    elif hand_placement_deviation > 0.15:
                        hand_bone_score = 0.5

                    feedback['errors'].append({
                        'criterion': 'hand_placement',
                        'improvement': threshold.get('tip', 'Place your hands closer to the edge of the box.'),
                        'measurement': f'{hand_placement_deviation:.3f}m deviation',
                        'severity': 'high' if hand_placement_deviation > 0.2 else 'medium'
                    })
                    feedback['score'] -= 0.3

                feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                    hand_bone_score,
                    [segment_map[(self.JOINT_MAP['left_elbow'], self.JOINT_MAP['left_wrist'])],
                     segment_map[(self.JOINT_MAP['right_elbow'], self.JOINT_MAP['right_wrist'])]],
                    feedback['bone_scores']
                )
            else:
                # Box not detected - cannot evaluate hand placement
                feedback['measurements']['hand_placement_deviation'] = None
                feedback['errors'].append({
                    'criterion': 'hand_placement',
                    'improvement': 'Vault box not detected in frame - ensure box is visible',
                    'measurement': 'N/A',
                    'severity': 'low'
                })

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_flight2(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Flight2', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0,
            'bone_scores': {i: 1.0 for i in range(10)}
        }

        segment_map = self._get_segment_map()

        # 1. Legs spread straight
        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        left_knee = pose_3d[self.JOINT_MAP['left_knee']]
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        right_hip = pose_3d[self.JOINT_MAP['right_hip']]
        right_knee = pose_3d[self.JOINT_MAP['right_knee']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]

        left_leg_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        avg_leg_angle = (left_leg_angle + right_leg_angle) / 2
        feedback['measurements']['avg_leg_angle'] = avg_leg_angle

        if 'legs_spread' in criteria:
            threshold = criteria['legs_spread']
            min_angle = threshold.get('min', 160)

            leg_bone_score = 1.0
            if avg_leg_angle < min_angle:
                if avg_leg_angle < 140:
                    leg_bone_score = 0.0
                elif avg_leg_angle < 150:
                    leg_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'legs_spread',
                    'improvement': threshold.get('tip', 'Spread your legs straight and wide.'),
                    'measurement': f'{avg_leg_angle:.1f}° (min: {min_angle}°)',
                    'severity': 'high' if avg_leg_angle < 140 else 'medium'
                })
                feedback['score'] -= 0.3

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                leg_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['left_knee'])],
                 segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],
                 segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],
                feedback['bone_scores']
            )

        # 2. Torso upright and balanced
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        torso_angle = self.calculate_angle(left_hip, left_shoulder, pose_3d[self.JOINT_MAP['right_shoulder']])
        feedback['measurements']['torso_angle'] = torso_angle

        if 'torso_upright' in criteria:
            threshold = criteria['torso_upright']
            min_angle = threshold.get('min', 170)
            max_angle = threshold.get('max', 190)

            torso_bone_score = 1.0
            if not (min_angle <= torso_angle <= max_angle):
                deviation = min(abs(torso_angle - min_angle), abs(torso_angle - max_angle))
                if deviation > 20:
                    torso_bone_score = 0.0
                elif deviation > 10:
                    torso_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'torso_upright',
                    'improvement': threshold.get('tip', 'Keep your torso upright and balanced.'),
                    'measurement': f'{torso_angle:.1f}° (target: {min_angle}-{max_angle}°)',
                    'severity': 'high' if deviation > 20 else 'medium'
                })
                feedback['score'] -= 0.2

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                torso_bone_score,
                [segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder'])],  # Shoulder Line
                 segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])]],  # Hip Line
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_landing(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Landing', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0,
            'bone_scores': {i: 1.0 for i in range(10)}
        }

        segment_map = self._get_segment_map()

        # 1. Controlled, stable landing in balance
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]
        feet_distance = self.calculate_distance(left_ankle, right_ankle)
        feedback['measurements']['feet_distance'] = feet_distance

        if 'stable_landing' in criteria:
            threshold = criteria['stable_landing']
            max_distance = threshold.get('max', 0.3)

            landing_bone_score = 1.0
            if feet_distance > max_distance:
                if feet_distance > 0.5:
                    landing_bone_score = 0.0
                elif feet_distance > 0.4:
                    landing_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'stable_landing',
                    'improvement': threshold.get('tip', 'Land with feet together for stability.'),
                    'measurement': f'{feet_distance:.3f}m apart (max: {max_distance}m)',
                    'severity': 'high' if feet_distance > 0.5 else 'medium'
                })
                feedback['score'] -= 0.3

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                landing_bone_score,
                [segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback
