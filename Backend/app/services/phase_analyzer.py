from typing import List, Dict
from app.models.schemas import AnalysisResult, PhaseGrade, PhaseType
from app.utils.calculations import calculate_angle, get_lanmark_coord, calculate_distance
from app.config import settings
import numpy as np

class PhaseAnalyzer:
    """
    Analyzes handstand video and grades 5 phases:
    1. Starting Position - 34 correct / 39 incorrect
    2. Upswing - 69 correct / 4 incorrect
    3. Hand Placement - 70 correct / 3 incorrect
    4. Body Position - 46 correct / 27 incorrect
    5. Landing & Finishing - 41 correct / 32 incorrect
    """
    
    def analyze(self, landmarks_data: List[Dict], filename: str) -> AnalysisResult:
        """
        Main analysis method
        """
        total_frames = len(landmarks_data)
        
        # Segment video into 5 phases
        phases_data = self._segment_phases(landmarks_data)
        
        # Grade each phase
        phase_grades = []
        correct_count = 0
        error_count = 0
        
        for phase_type, frames in phases_data.items():
            grade = self._grade_phase(phase_type, frames)
            phase_grades.append(grade)
            
            if grade.is_correct:
                correct_count += 1
            else:
                error_count += 1
        
        # Calculate overall score
        overall_score = np.mean([g.score for g in phase_grades])
        
        return AnalysisResult(
            video_filename=filename,
            overall_score=round(overall_score, 2),
            total_correct_phases=correct_count,
            total_error_phases=error_count,
            phases=phase_grades,
            total_frames=total_frames,
            duration_seconds=total_frames / 30.0  # Assuming 30fps
        )
    
    def _segment_phases(self, landmarks_data: List[Dict]) -> Dict[PhaseType, List[Dict]]:
        """
        Segment video into 5 phases based on body position and movement
        
        For testing purposes, using simplified time-based segmentation.
        In production, you would detect actual movement patterns.
        """
        total_frames = len(landmarks_data)
        
        # Phase 1: Starting position (first 15% of video)
        phase1_end = int(total_frames * 0.15)
        
        # Phase 2: Upswing (15-35% of video)
        phase2_end = int(total_frames * 0.35)
        
        # Phase 3: Hand placement (35-45% of video)
        phase3_end = int(total_frames * 0.45)
        
        # Phase 4: Body position/hold (45-80% of video)
        phase4_end = int(total_frames * 0.80)
        
        # Phase 5: Landing & finishing (80-100% of video)
        phase5_end = int(total_frames) #revert to empty if stopped working
        
        return {
            PhaseType.STARTING_POSITION: landmarks_data[0:phase1_end],
            PhaseType.UPSWING: landmarks_data[phase1_end:phase2_end],
            PhaseType.HAND_PLACEMENT: landmarks_data[phase2_end:phase3_end],
            PhaseType.BODY_POSITION: landmarks_data[phase3_end:phase4_end],
            PhaseType.LANDING_FINISHING: landmarks_data[phase5_end:]
        }
    
    def _grade_phase(self, phase_type: PhaseType, frames: List[Dict]) -> PhaseGrade:
        """
        Grade a specific phase based on criteria
        """
        if phase_type == PhaseType.STARTING_POSITION:
            return self._grade_starting_position(frames)
        elif phase_type == PhaseType.UPSWING:
            return self._grade_upswing(frames)
        elif phase_type == PhaseType.HAND_PLACEMENT:
            return self._grade_hand_placement(frames)
        elif phase_type == PhaseType.BODY_POSITION:
            return self._grade_body_position(frames)
        elif phase_type == PhaseType.LANDING_FINISHING:
            return self._grade_landing_finishing(frames)
    
    def _grade_starting_position(self, frames: List[Dict]) -> PhaseGrade:
        """
        Grade starting position:
        - Proper stance (feet shoulder-width apart)
        - Arms ready (raised or preparing)
        - Body alignment (straight posture)

        Success rate: 34/(34+39) = 46.6%
        """
        if not frames:
            return self._create_empty_grade(PhaseType.STARTING_POSITION, "Starting Position")

        # Analyze first few frames for starting position
        sample_frames = frames[:min(5, len(frames))]

        stance_widths = []
        forward_leans = []
        arm_positions = []

        for frame in sample_frames:
            landmarks = frame.get('landmarks', {})

            # MediaPipe indices: 11=left_shoulder, 12=right_shoulder, 23=left_hip, 24=right_hip
            # 27=left_ankle, 28=right_ankle
            left_shoulder = get_lanmark_coord(landmarks, 11)
            right_shoulder = get_lanmark_coord(landmarks, 12)
            left_hip = get_lanmark_coord(landmarks, 23)
            right_hip = get_lanmark_coord(landmarks, 24)
            left_ankle = get_lanmark_coord(landmarks, 27)
            right_ankle = get_lanmark_coord(landmarks, 28)

            # Calculate stance width (distance between ankles relative to shoulder width)
            ankle_distance = calculate_distance(left_ankle, right_ankle)
            shoulder_distance = calculate_distance(left_shoulder, right_shoulder)
            if shoulder_distance > 0:
                stance_ratio = ankle_distance / shoulder_distance
                stance_widths.append(stance_ratio)

            # Calculate forward lean (hip to shoulder vertical alignment)
            mid_hip = {
                'x': (left_hip['x'] + right_hip['x']) / 2,
                'y': (left_hip['y'] + right_hip['y']) / 2,
                'z': (left_hip['z'] + right_hip['z']) / 2
            }
            mid_shoulder = {
                'x': (left_shoulder['x'] + right_shoulder['x']) / 2,
                'y': (left_shoulder['y'] + right_shoulder['y']) / 2,
                'z': (left_shoulder['z'] + right_shoulder['z']) / 2
            }
            # Forward lean in degrees (deviation from vertical)
            forward_lean = abs(mid_shoulder['x'] - mid_hip['x']) * 100
            forward_leans.append(forward_lean)

            # Arm position (shoulder angle)
            left_elbow = get_lanmark_coord(landmarks, 13)
            arm_angle = calculate_angle(left_hip, left_shoulder, left_elbow)
            arm_positions.append(arm_angle)

        # Average metrics
        avg_stance_width = np.mean(stance_widths) if stance_widths else 0.0
        avg_forward_lean = np.mean(forward_leans) if forward_leans else 0.0
        avg_arm_position = np.mean(arm_positions) if arm_positions else 0.0

        # Scoring logic
        errors = []
        score_components = []

        # Stance width should be ~0.8-1.2 (shoulder-width apart)
        if 0.8 <= avg_stance_width <= 1.2:
            score_components.append(95.0)
        elif 0.6 <= avg_stance_width <= 1.4:
            score_components.append(75.0)
        else:
            score_components.append(50.0)
            errors.append(f"Feet position unclear (ratio: {avg_stance_width:.2f})")

        # Forward lean should be minimal (<10)
        if avg_forward_lean < 10:
            score_components.append(90.0)
        elif avg_forward_lean < 20:
            score_components.append(70.0)
        else:
            score_components.append(50.0)
            errors.append(f"Upper body lean detected ({avg_forward_lean:.1f}°)")

        # Arm position (ready position, arms should be somewhat raised)
        if avg_arm_position > 100:
            score_components.append(85.0)
        else:
            score_components.append(65.0)
            errors.append("Arms not in ready position")

        score = np.mean(score_components)
        is_correct = score >= settings.PASSING_SCORE

        feedback = "Good starting stance" if is_correct else "Starting position needs adjustment"

        return PhaseGrade(
            phase=PhaseType.STARTING_POSITION,
            phase_name="Starting Position",
            score=round(score, 2),
            is_correct=is_correct,
            feedback=feedback,
            key_metrics={
                "stance_width": round(avg_stance_width, 2),
                "forward_lean": round(avg_forward_lean, 2),
                "arm_position": round(avg_arm_position, 2)
            },
            frame_range=(frames[0]['frame_number'], frames[-1]['frame_number']),
            error_details=errors
        )
    
    def _grade_upswing(self, frames: List[Dict]) -> PhaseGrade:
        """
        Grade upswing:
        - Smooth momentum generation
        - Leg coordination
        - Power and timing

        Success rate: 69/(69+4) = 94.5%
        """
        if not frames:
            return self._create_empty_grade(PhaseType.UPSWING, "Upswing")

        leg_lift_angles = []
        hip_velocities = []
        prev_hip_y = None

        for frame in frames:
            landmarks = frame.get('landmarks', {})

            # Calculate leg lift angle (hip-knee-ankle)
            left_hip = get_lanmark_coord(landmarks, 23)
            left_knee = get_lanmark_coord(landmarks, 25)
            left_ankle = get_lanmark_coord(landmarks, 27)

            leg_angle = calculate_angle(left_hip, left_knee, left_ankle)
            leg_lift_angles.append(leg_angle)

            # Calculate hip velocity (momentum indicator)
            if prev_hip_y is not None:
                velocity = abs(left_hip['y'] - prev_hip_y)
                hip_velocities.append(velocity)
            prev_hip_y = left_hip['y']

        # Calculate metrics
        max_leg_lift = np.max(leg_lift_angles) if leg_lift_angles else 0.0
        avg_velocity = np.mean(hip_velocities) if hip_velocities else 0.0

        # Smoothness: standard deviation of velocities (lower is smoother)
        smoothness_raw = np.std(hip_velocities) if len(hip_velocities) > 1 else 1.0
        smoothness = max(0.0, 1.0 - smoothness_raw)

        # Scoring logic
        errors = []
        score_components = []

        # Leg lift should reach at least 120 degrees
        if max_leg_lift >= 140:
            score_components.append(95.0)
        elif max_leg_lift >= 120:
            score_components.append(85.0)
        else:
            score_components.append(60.0)
            errors.append(f"Insufficient leg drive (max angle: {max_leg_lift:.1f}°)")

        # Momentum should be good (velocity > 0.01)
        if avg_velocity >= 0.015:
            score_components.append(95.0)
        elif avg_velocity >= 0.01:
            score_components.append(80.0)
        else:
            score_components.append(65.0)
            errors.append("Hesitation detected")

        # Smoothness should be high
        if smoothness >= 0.8:
            score_components.append(92.0)
        elif smoothness >= 0.6:
            score_components.append(75.0)
        else:
            score_components.append(60.0)

        score = np.mean(score_components)
        is_correct = score >= settings.PASSING_SCORE

        feedback = "Excellent upswing momentum" if is_correct else "Upswing lacks power"

        return PhaseGrade(
            phase=PhaseType.UPSWING,
            phase_name="Upswing",
            score=round(score, 2),
            is_correct=is_correct,
            feedback=feedback,
            key_metrics={
                "momentum_score": round(avg_velocity * 100, 2),
                "leg_lift_angle": round(max_leg_lift, 2),
                "smoothness": round(smoothness, 2)
            },
            frame_range=(frames[0]['frame_number'], frames[-1]['frame_number']),
            error_details=errors
        )
    
    def _grade_hand_placement(self, frames: List[Dict]) -> PhaseGrade:
        """
        Grade hand placement:
        - Proper hand positioning (shoulder-width apart)
        - Shoulder alignment over hands
        - Arm extension (straight arms)

        Success rate: 70/(70+3) = 95.9%
        """
        if not frames:
            return self._create_empty_grade(PhaseType.HAND_PLACEMENT, "Hand Placement")

        # Analyze middle frames when hands are placed
        mid_point = len(frames) // 2
        sample_frames = frames[max(0, mid_point - 2):min(len(frames), mid_point + 3)]

        hand_spacings = []
        arm_extensions = []
        shoulder_alignments = []

        for frame in sample_frames:
            landmarks = frame.get('landmarks', {})

            # Get wrist, elbow, shoulder positions
            left_wrist = get_lanmark_coord(landmarks, 15)
            right_wrist = get_lanmark_coord(landmarks, 16)
            left_elbow = get_lanmark_coord(landmarks, 13)
            right_elbow = get_lanmark_coord(landmarks, 14)
            left_shoulder = get_lanmark_coord(landmarks, 11)
            right_shoulder = get_lanmark_coord(landmarks, 12)

            # Calculate hand spacing relative to shoulder width
            hand_distance = calculate_distance(left_wrist, right_wrist)
            shoulder_distance = calculate_distance(left_shoulder, right_shoulder)
            if shoulder_distance > 0:
                spacing_ratio = hand_distance / shoulder_distance
                hand_spacings.append(spacing_ratio)

            # Calculate arm extension (should be ~180 degrees for straight arms)
            left_arm_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
            right_arm_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
            avg_arm_extension = (left_arm_angle + right_arm_angle) / 2
            arm_extensions.append(avg_arm_extension)

            # Shoulder alignment (shoulders should be over hands)
            # Check vertical alignment by comparing y-coordinates
            mid_wrist_y = (left_wrist['y'] + right_wrist['y']) / 2
            mid_shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            alignment_score = 1.0 - abs(mid_shoulder_y - mid_wrist_y)
            shoulder_alignments.append(max(0.0, alignment_score))

        # Average metrics
        avg_hand_spacing = np.mean(hand_spacings) if hand_spacings else 0.0
        avg_arm_extension = np.mean(arm_extensions) if arm_extensions else 0.0
        avg_shoulder_alignment = np.mean(shoulder_alignments) if shoulder_alignments else 0.0

        # Scoring logic
        errors = []
        score_components = []

        # Hand spacing should be ~0.8-1.2 (shoulder-width)
        if 0.8 <= avg_hand_spacing <= 1.2:
            score_components.append(95.0)
        elif 0.6 <= avg_hand_spacing <= 1.4:
            score_components.append(80.0)
            errors.append(f"Hand spacing slightly off (ratio: {avg_hand_spacing:.2f})")
        else:
            score_components.append(60.0)
            if avg_hand_spacing > 1.4:
                errors.append("Hands too wide")
            else:
                errors.append("Hands too narrow")

        # Arm extension should be close to 180 degrees
        if avg_arm_extension >= 165:
            score_components.append(95.0)
        elif avg_arm_extension >= 150:
            score_components.append(80.0)
        else:
            score_components.append(65.0)
            errors.append(f"Arms not fully extended ({avg_arm_extension:.1f}°)")

        # Shoulder alignment should be high
        if avg_shoulder_alignment >= 0.85:
            score_components.append(92.0)
        elif avg_shoulder_alignment >= 0.70:
            score_components.append(75.0)
        else:
            score_components.append(60.0)
            errors.append("Uneven placement")

        score = np.mean(score_components)
        is_correct = score >= settings.PASSING_SCORE

        feedback = "Perfect hand placement" if is_correct else "Hand placement needs work"

        return PhaseGrade(
            phase=PhaseType.HAND_PLACEMENT,
            phase_name="Hand Placement",
            score=round(score, 2),
            is_correct=is_correct,
            feedback=feedback,
            key_metrics={
                "hand_shoulder_alignment": round(avg_shoulder_alignment, 2),
                "arm_extension": round(avg_arm_extension, 2),
                "hand_spacing": round(avg_hand_spacing, 2)
            },
            frame_range=(frames[0]['frame_number'], frames[-1]['frame_number']),
            error_details=errors
        )
    
    def _grade_body_position(self, frames: List[Dict]) -> PhaseGrade:
        """
        Grade body position during hold:
        - Vertical alignment (straight line from hands to feet)
        - Body tension and control
        - Balance stability

        Success rate: 46/(46+27) = 63.0%
        """
        if not frames:
            return self._create_empty_grade(PhaseType.BODY_POSITION, "Body Position")

        vertical_angles = []
        hip_angles = []
        shoulder_angles = []
        balance_scores = []

        for frame in frames:
            landmarks = frame.get('landmarks', {})

            # Get key body points
            left_shoulder = get_lanmark_coord(landmarks, 11)
            right_shoulder = get_lanmark_coord(landmarks, 12)
            left_hip = get_lanmark_coord(landmarks, 23)
            right_hip = get_lanmark_coord(landmarks, 24)
            left_ankle = get_lanmark_coord(landmarks, 27)
            right_ankle = get_lanmark_coord(landmarks, 28)
            left_wrist = get_lanmark_coord(landmarks, 15)

            # Calculate mid-points
            mid_shoulder = {
                'x': (left_shoulder['x'] + right_shoulder['x']) / 2,
                'y': (left_shoulder['y'] + right_shoulder['y']) / 2,
                'z': (left_shoulder['z'] + right_shoulder['z']) / 2
            }
            mid_hip = {
                'x': (left_hip['x'] + right_hip['x']) / 2,
                'y': (left_hip['y'] + right_hip['y']) / 2,
                'z': (left_hip['z'] + right_hip['z']) / 2
            }
            mid_ankle = {
                'x': (left_ankle['x'] + right_ankle['x']) / 2,
                'y': (left_ankle['y'] + right_ankle['y']) / 2,
                'z': (left_ankle['z'] + right_ankle['z']) / 2
            }

            # Calculate vertical alignment (shoulder-hip-ankle should be ~180 degrees)
            vertical_angle = calculate_angle(mid_shoulder, mid_hip, mid_ankle)
            vertical_angles.append(vertical_angle)

            # Calculate hip angle (to detect "banana back")
            left_knee = get_lanmark_coord(landmarks, 25)
            hip_angle = calculate_angle(left_shoulder, left_hip, left_knee)
            hip_angles.append(hip_angle)

            # Calculate shoulder angle (shoulder-elbow-wrist for stability)
            left_elbow = get_lanmark_coord(landmarks, 13)
            shoulder_angle = calculate_angle(left_wrist, left_shoulder, left_hip)
            shoulder_angles.append(shoulder_angle)

            # Balance score (how centered the body is)
            # Check horizontal alignment of shoulders and hips
            shoulder_hip_diff = abs(mid_shoulder['x'] - mid_hip['x'])
            balance_score = max(0.0, 1.0 - shoulder_hip_diff * 10)
            balance_scores.append(balance_score)

        # Calculate average metrics
        avg_vertical_angle = np.mean(vertical_angles) if vertical_angles else 0.0
        avg_hip_angle = np.mean(hip_angles) if hip_angles else 0.0
        avg_shoulder_angle = np.mean(shoulder_angles) if shoulder_angles else 0.0
        avg_balance = np.mean(balance_scores) if balance_scores else 0.0
        hold_duration = len(frames)

        # Scoring logic
        errors = []
        score_components = []

        # Vertical alignment should be close to 180 degrees (straight line)
        if avg_vertical_angle >= 170:
            score_components.append(95.0)
        elif avg_vertical_angle >= 160:
            score_components.append(80.0)
        else:
            score_components.append(60.0)
            errors.append(f"Body not vertical (angle: {avg_vertical_angle:.1f}°)")

        # Hip angle should be ~175-180 (straight body, no banana back)
        if avg_hip_angle >= 170:
            score_components.append(90.0)
        elif avg_hip_angle >= 160:
            score_components.append(75.0)
            errors.append(f"Hip angle off ({avg_hip_angle:.1f}°)")
        else:
            score_components.append(55.0)
            errors.append("Banana back detected")

        # Shoulder angle indicates stability
        if 85 <= avg_shoulder_angle <= 95:
            score_components.append(88.0)
        elif 75 <= avg_shoulder_angle <= 105:
            score_components.append(70.0)
        else:
            score_components.append(60.0)
            errors.append("Shoulder instability")

        # Balance should be high
        if avg_balance >= 0.85:
            score_components.append(90.0)
        elif avg_balance >= 0.70:
            score_components.append(75.0)
        else:
            score_components.append(60.0)
            errors.append("Balance instability")

        # Hold duration bonus (longer hold = better control)
        if hold_duration >= 20:
            score_components.append(85.0)
        elif hold_duration >= 10:
            score_components.append(75.0)
        else:
            score_components.append(65.0)

        score = np.mean(score_components)
        is_correct = score >= settings.PASSING_SCORE

        feedback = "Body position maintained" if is_correct else "Body alignment issues detected"

        return PhaseGrade(
            phase=PhaseType.BODY_POSITION,
            phase_name="Body Position",
            score=round(score, 2),
            is_correct=is_correct,
            feedback=feedback,
            key_metrics={
                "vertical_angle": round(avg_vertical_angle, 2),
                "hip_angle": round(avg_hip_angle, 2),
                "shoulder_angle": round(avg_shoulder_angle, 2),
                "hold_duration_frames": hold_duration
            },
            frame_range=(frames[0]['frame_number'], frames[-1]['frame_number']),
            error_details=errors
        )
    
    def _grade_landing_finishing(self, frames: List[Dict]) -> PhaseGrade:
        """
        Grade landing and finish:
        - Controlled descent
        - Landing stability and balance
        - Final position control

        Success rate: 41/(41+32) = 56.2%
        """
        if not frames:
            return self._create_empty_grade(PhaseType.LANDING_FINISHING, "Landing & Finishing")

        descent_speeds = []
        landing_balances = []
        prev_hip_y = None

        # Analyze descent speed (first half of frames)
        descent_frames = frames[:len(frames) // 2] if len(frames) > 2 else frames

        for frame in descent_frames:
            landmarks = frame.get('landmarks', {})
            left_hip = get_lanmark_coord(landmarks, 23)

            # Calculate descent speed
            if prev_hip_y is not None:
                speed = abs(left_hip['y'] - prev_hip_y)
                descent_speeds.append(speed)
            prev_hip_y = left_hip['y']

        # Analyze landing balance (last few frames)
        landing_frames = frames[-min(5, len(frames)):]

        for frame in landing_frames:
            landmarks = frame.get('landmarks', {})

            # Check balance by measuring foot spacing and body stability
            left_ankle = get_lanmark_coord(landmarks, 27)
            right_ankle = get_lanmark_coord(landmarks, 28)
            left_hip = get_lanmark_coord(landmarks, 23)
            right_hip = get_lanmark_coord(landmarks, 24)

            # Calculate center of mass alignment
            mid_ankle_x = (left_ankle['x'] + right_ankle['x']) / 2
            mid_hip_x = (left_hip['x'] + right_hip['x']) / 2
            balance_diff = abs(mid_hip_x - mid_ankle_x)
            balance_score = max(0.0, 1.0 - balance_diff * 5)
            landing_balances.append(balance_score)

        # Calculate final position score (last frame stability)
        final_frame = frames[-1]
        final_landmarks = final_frame.get('landmarks', {})

        left_shoulder = get_lanmark_coord(final_landmarks, 11)
        right_shoulder = get_lanmark_coord(final_landmarks, 12)
        left_hip = get_lanmark_coord(final_landmarks, 23)
        right_hip = get_lanmark_coord(final_landmarks, 24)

        # Check if body is upright in final position
        mid_shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2
        mid_hip_y = (left_hip['y'] + right_hip['y']) / 2
        upright_score = max(0.0, 1.0 - abs(mid_shoulder_y - mid_hip_y - 0.3))

        # Average metrics
        avg_descent_speed = np.mean(descent_speeds) if descent_speeds else 0.0
        avg_landing_balance = np.mean(landing_balances) if landing_balances else 0.0
        final_position_score = upright_score

        # Scoring logic
        errors = []
        score_components = []

        # Descent speed should be controlled (not too fast, not too slow)
        if 0.005 <= avg_descent_speed <= 0.02:
            score_components.append(85.0)
        elif 0.02 < avg_descent_speed <= 0.03:
            score_components.append(70.0)
            errors.append("Rushed descent")
        elif avg_descent_speed > 0.03:
            score_components.append(55.0)
            errors.append("Rushed descent")
        else:
            score_components.append(65.0)

        # Landing balance should be high
        if avg_landing_balance >= 0.75:
            score_components.append(85.0)
        elif avg_landing_balance >= 0.60:
            score_components.append(70.0)
        else:
            score_components.append(55.0)
            errors.append("Loss of balance on landing")

        # Final position should be controlled
        if final_position_score >= 0.70:
            score_components.append(80.0)
        elif final_position_score >= 0.50:
            score_components.append(70.0)
        else:
            score_components.append(60.0)
            errors.append("Final position unstable")

        score = np.mean(score_components)
        is_correct = score >= settings.PASSING_SCORE

        feedback = "Controlled landing" if is_correct else "Landing needs more control"

        return PhaseGrade(
            phase=PhaseType.LANDING_FINISHING,
            phase_name="Landing & Finishing",
            score=round(score, 2),
            is_correct=is_correct,
            feedback=feedback,
            key_metrics={
                "descent_speed": round(avg_descent_speed * 100, 2),
                "landing_balance": round(avg_landing_balance, 2),
                "final_position_score": round(final_position_score, 2)
            },
            frame_range=(frames[0]['frame_number'], frames[-1]['frame_number']),
            error_details=errors
        )

    def _create_empty_grade(self, phase_type: PhaseType, phase_name: str) -> PhaseGrade:
        """
        Create an empty grade when no frames are available
        """
        return PhaseGrade(
            phase=phase_type,
            phase_name=phase_name,
            score=0.0,
            is_correct=False,
            feedback="No data available for this phase",
            key_metrics={},
            frame_range=(0, 0),
            error_details=["No frames available for analysis"]
        )