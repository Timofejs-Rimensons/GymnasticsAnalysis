import numpy as np
from typing import Dict, List
from services.BaseAnalyticsService import BaseAnalyticsService

class HandstandAnalyticsService(BaseAnalyticsService):
    """
    Analyzes pose geometry for a handstand and provides actionable feedback.
    Uses 3D world coordinates from MediaPipe (13 joints).
    """

    def analyze_pose(self, pose_3d: np.ndarray, pose_name: str) -> Dict:
        """
        Analyze a pose and return detailed feedback.

        Args:
            pose_3d: (13, 3) array of joint positions
            pose_name: Name of the pose phase

        Returns:
            Analysis results with measurements, errors, overall score, and bone_scores.
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
                'score': 0.0,
                'bone_scores': {i: 1.0 for i in range(10)} # Default perfect score for all bones
            }

    def analyze_starting_position(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Starting', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0, # Start with perfect score
            'bone_scores': {i: 1.0 for i in range(10)} # Initialize all bone scores to perfect
        }
        
        segment_map = self._get_segment_map()
        
        # 1. Arms up
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        left_elbow = pose_3d[self.JOINT_MAP['left_elbow']]
        left_vertical = left_shoulder.copy()
        left_vertical[1] += 1.0 # 1 meter up in y-direction
        left_arm_angle = self.calculate_angle(left_vertical, left_shoulder, left_elbow)
        feedback['measurements']['left_arm_angle'] = left_arm_angle

        if 'arms_vertical_angle' in criteria:
            threshold = criteria['arms_vertical_angle']
            min_angle = threshold.get('min', 0)
            max_angle = threshold.get('max', 180) 
            
            arm_bone_score = 1.0 # Default good
            if not (min_angle <= left_arm_angle <= max_angle):
                deviation = min(abs(left_arm_angle - min_angle), abs(left_arm_angle - max_angle))
                if deviation > 30: # Example threshold for 'bad'
                    arm_bone_score = 0.0
                elif deviation > 15: # Example threshold for 'mid'
                    arm_bone_score = 0.5
                
                feedback['errors'].append({
                    'criterion': 'arms_vertical_angle',
                    'improvement': threshold.get('tip', 'Raise your arms higher.'),
                })
                feedback['score'] -= 0.3 # Fixed penalty

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                arm_bone_score,
                [segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['left_elbow'])], # Left Upper Arm
                 segment_map[(self.JOINT_MAP['right_shoulder'], self.JOINT_MAP['right_elbow'])]], # Right Upper Arm
                feedback['bone_scores']
            )

        # 2. Back leg straight
        right_hip = pose_3d[self.JOINT_MAP['right_hip']]
        right_knee = pose_3d[self.JOINT_MAP['right_knee']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]
        back_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        feedback['measurements']['back_knee_angle'] = back_knee_angle

        if 'back_leg_knee_angle' in criteria:
            threshold = criteria['back_leg_knee_angle']
            min_angle = threshold.get('min', 170)
            max_angle = 180 # Optimal for straight leg
            
            leg_bone_score = 1.0 # Default good
            if back_knee_angle < min_angle:
                deviation = max_angle - back_knee_angle
                if deviation > 30: # Example threshold for 'bad'
                    leg_bone_score = 0.0
                elif deviation > 15: # Example threshold for 'mid'
                    leg_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'back_leg_straight',
                    'improvement': threshold.get('tip', 'Straighten your back leg.'),
                })
                feedback['score'] -= 0.35 # Fixed penalty

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                leg_bone_score,
                [segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],   # Right Thigh
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],# Right Shin
                feedback['bone_scores']
            )

        # 3. Step distance
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]
        step_distance = self.calculate_distance(left_ankle, right_ankle)
        feedback['measurements']['step_distance'] = step_distance

        if 'step_distance' in criteria:
            threshold = criteria['step_distance']
            min_dist = threshold.get('min', 0)
            max_dist = threshold.get('max', 10)

            step_bone_score = 1.0 # Default good
            if not (min_dist <= step_distance <= max_dist):
                deviation = min(abs(step_distance - min_dist), abs(step_distance - max_dist))
                if deviation > 0.4: # Example threshold for 'bad'
                    step_bone_score = 0.0
                elif deviation > 0.2: # Example threshold for 'mid'
                    step_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'step_distance',
                    'improvement': threshold.get('tip', 'Adjust your step distance.'),
                })
                feedback['score'] -= 0.1 # Fixed penalty
            
            # Step distance could affect hip line for visualization
            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                step_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])]], # Hip Line
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_swing(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Swing', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0, # Start with perfect score
            'bone_scores': {i: 1.0 for i in range(10)}
        }
        
        segment_map = self._get_segment_map()
        
        right_hip = pose_3d[self.JOINT_MAP['right_hip']]
        right_knee = pose_3d[self.JOINT_MAP['right_knee']]
        right_ankle = pose_3d[self.JOINT_MAP['right_ankle']]
        back_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        feedback['measurements']['back_knee_angle'] = back_knee_angle

        if 'back_leg_knee_angle' in criteria:
            threshold = criteria['back_leg_knee_angle']
            min_angle = threshold.get('min', 170)
            max_angle = 180
            
            leg_bone_score = 1.0 # Default good
            if back_knee_angle < min_angle:
                deviation = max_angle - back_knee_angle
                if deviation > 30: # Example threshold for 'bad'
                    leg_bone_score = 0.0
                elif deviation > 15: # Example threshold for 'mid'
                    leg_bone_score = 0.5

                feedback['errors'].append({
                    'criterion': 'back_leg_straight',
                    'improvement': threshold.get('tip', 'Keep back leg straight.'),
                })
                feedback['score'] -= 0.5 # Fixed penalty

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                leg_bone_score,
                [segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],   # Right Thigh
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],# Right Shin
                feedback['bone_scores']
            )
        
        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_handstand(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Handstand', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0, # Start with perfect score
            'bone_scores': {i: 1.0 for i in range(10)}
        }
        
        segment_map = self._get_segment_map()
        
        shoulder = (pose_3d[self.JOINT_MAP['left_shoulder']] + pose_3d[self.JOINT_MAP['right_shoulder']]) / 2
        hip = (pose_3d[self.JOINT_MAP['left_hip']] + pose_3d[self.JOINT_MAP['right_hip']]) / 2
        ankle = (pose_3d[self.JOINT_MAP['left_ankle']] + pose_3d[self.JOINT_MAP['right_ankle']]) / 2
        
        # 1. Body alignment
        leg_alignment_deviation = self.calculate_vertical_alignment([ankle, hip, shoulder])
        feedback['measurements']['leg_alignment_deviation'] = leg_alignment_deviation
        
        if 'leg_alignment_deviation' in criteria:
            threshold = criteria['leg_alignment_deviation']
            max_deviation = threshold.get('max', 0.15)
            
            alignment_bone_score = 1.0 # Default good
            if leg_alignment_deviation > max_deviation:
                if leg_alignment_deviation > 0.3: # Example threshold for 'bad'
                    alignment_bone_score = 0.0
                elif leg_alignment_deviation > 0.2: # Example threshold for 'mid'
                    alignment_bone_score = 0.5

                feedback['errors'].append({'criterion': 'leg_alignment', 'improvement': criteria['leg_alignment_deviation'].get('tip')})
                feedback['score'] -= 0.3 # Fixed penalty
            
            # Affects entire body alignment
            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                alignment_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])], # Hip Line
                 segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder'])], # Shoulder Line
                 segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['left_knee'])],
                 segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],
                 segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],
                feedback['bone_scores']
            )

        # 2. Back straightness
        back_angle = self.calculate_angle(shoulder, hip, ankle)
        back_straightness = abs(180 - back_angle)
        feedback['measurements']['back_straightness'] = back_straightness
        
        if 'back_straightness' in criteria:
            threshold = criteria['back_straightness']
            max_deviation = threshold.get('max', 10)
            
            back_bone_score = 1.0 # Default good
            if back_straightness > max_deviation:
                if back_straightness > 20: # Example threshold for 'bad'
                    back_bone_score = 0.0
                elif back_straightness > 10: # Example threshold for 'mid'
                    back_bone_score = 0.5

                feedback['errors'].append({'criterion': 'back_straightness', 'improvement': criteria['back_straightness'].get('tip')})
                feedback['score'] -= 0.25 # Fixed penalty
            
            # Affects torso and potentially legs if severe
            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                back_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['right_hip'])], # Hip Line (torso proxy)
                 segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['right_shoulder'])]], # Shoulder Line
                feedback['bone_scores']
            )

        # 3. Hand width
        left_wrist = pose_3d[self.JOINT_MAP['left_wrist']]
        right_wrist = pose_3d[self.JOINT_MAP['right_wrist']]
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        right_shoulder = pose_3d[self.JOINT_MAP['right_shoulder']]
        
        hand_width = self.calculate_distance(left_wrist, right_wrist)
        shoulder_width = self.calculate_distance(left_shoulder, right_shoulder)
        hand_width_ratio = hand_width / shoulder_width if shoulder_width > 0 else 0
        feedback['measurements']['hand_width_ratio'] = hand_width_ratio

        if 'hand_width_ratio' in criteria:
            threshold = criteria['hand_width_ratio']
            min_ratio = threshold.get('min', 0.9)
            max_ratio = threshold.get('max', 1.3)

            hand_bone_score = 1.0 # Default good
            if not (min_ratio <= hand_width_ratio <= max_ratio):
                deviation = min(abs(hand_width_ratio - min_ratio), abs(hand_width_ratio - max_ratio))
                if deviation > 0.3: # Example threshold for 'bad'
                    hand_bone_score = 0.0
                elif deviation > 0.15: # Example threshold for 'mid'
                    hand_bone_score = 0.5

                feedback['errors'].append({'criterion': 'hand_placement', 'improvement': criteria['hand_width_ratio'].get('tip')})
                feedback['score'] -= 0.15 # Fixed penalty
            
            # Affects wrists segments
            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                hand_bone_score,
                [segment_map[(self.JOINT_MAP['left_elbow'], self.JOINT_MAP['left_wrist'])],    # Left Forearm
                 segment_map[(self.JOINT_MAP['right_elbow'], self.JOINT_MAP['right_wrist'])]],    # Right Forearm
                feedback['bone_scores']
            )

        # 4. Shoulders over arms
        left_wrist = pose_3d[self.JOINT_MAP['left_wrist']]
        left_shoulder = pose_3d[self.JOINT_MAP['left_shoulder']]
        left_elbow = pose_3d[self.JOINT_MAP['left_elbow']]
        
        shoulder_arm_alignment = self.calculate_vertical_alignment([left_wrist, left_elbow, left_shoulder])
        feedback['measurements']['shoulder_arm_alignment'] = shoulder_arm_alignment
        
        if 'shoulder_arm_alignment' in criteria:
            threshold = criteria['shoulder_arm_alignment']
            max_deviation = threshold.get('max', 0.1)
            
            arm_alignment_bone_score = 1.0 # Default good
            if shoulder_arm_alignment > max_deviation:
                if shoulder_arm_alignment > 0.2: # Example threshold for 'bad'
                    arm_alignment_bone_score = 0.0
                elif shoulder_arm_alignment > 0.1: # Example threshold for 'mid'
                    arm_alignment_bone_score = 0.5

                feedback['errors'].append({'criterion': 'shoulder_position', 'improvement': criteria['shoulder_arm_alignment'].get('tip')})
                feedback['score'] -= 0.2 # Fixed penalty

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                arm_alignment_bone_score,
                [segment_map[(self.JOINT_MAP['left_shoulder'], self.JOINT_MAP['left_elbow'])],    # Left Upper Arm
                 segment_map[(self.JOINT_MAP['left_elbow'], self.JOINT_MAP['left_wrist'])],       # Left Forearm
                 segment_map[(self.JOINT_MAP['right_shoulder'], self.JOINT_MAP['right_elbow'])],  # Right Upper Arm
                 segment_map[(self.JOINT_MAP['right_elbow'], self.JOINT_MAP['right_wrist'])]],    # Right Forearm
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback

    def analyze_landing(self, pose_3d: np.ndarray) -> Dict:
        criteria = self.config.get('Landing', {}).get('criteria', {})
        feedback = {
            'measurements': {},
            'errors': [],
            'score': 1.0, # Start with perfect score
            'bone_scores': {i: 1.0 for i in range(10)}
        }
        
        segment_map = self._get_segment_map()

        left_hip = pose_3d[self.JOINT_MAP['left_hip']]
        left_knee = pose_3d[self.JOINT_MAP['left_knee']]
        left_ankle = pose_3d[self.JOINT_MAP['left_ankle']]
        
        knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        feedback['measurements']['avg_knee_flexion'] = knee_angle
        
        if 'knee_flexion' in criteria:
            threshold = criteria['knee_flexion']
            min_angle = threshold.get('min', 90)
            max_angle = threshold.get('max', 140)
            
            knee_bone_score = 1.0 # Default good
            if not (min_angle <= knee_angle <= max_angle):
                deviation = min(abs(knee_angle - min_angle), abs(knee_angle - max_angle))
                if deviation > 40: # Example threshold for 'bad'
                    knee_bone_score = 0.0
                elif deviation > 20: # Example threshold for 'mid'
                    knee_bone_score = 0.5

                feedback['errors'].append({'criterion': 'knee_flexion', 'improvement': threshold.get('tip')})
                feedback['score'] -= 0.3 # Fixed penalty

            feedback['bone_scores'] = self._calculate_bone_scores_from_criterion(
                knee_bone_score,
                [segment_map[(self.JOINT_MAP['left_hip'], self.JOINT_MAP['left_knee'])],    # Left Thigh
                 segment_map[(self.JOINT_MAP['left_knee'], self.JOINT_MAP['left_ankle'])],   # Left Shin
                 segment_map[(self.JOINT_MAP['right_hip'], self.JOINT_MAP['right_knee'])],   # Right Thigh
                 segment_map[(self.JOINT_MAP['right_knee'], self.JOINT_MAP['right_ankle'])]],# Right Shin
                feedback['bone_scores']
            )

        feedback['score'] = max(0.0, feedback['score'])
        return feedback