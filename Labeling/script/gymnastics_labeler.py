import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
from pathlib import Path
from typing import List, Dict, Tuple
import math


class GymnasticsPoseLabeler:
    """
    Automatic pose detection and labeling for gymnastics videos using MediaPipe.
    Detects: starting, swing, handstand, landing
    """
    
    def __init__(self, confidence_threshold=0.5):
        """
        Initialize MediaPipe Pose detector
        
        Args:
            confidence_threshold: Minimum confidence for pose detection
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=confidence_threshold,
            min_tracking_confidence=confidence_threshold
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Pose labels
        self.STARTING = 0
        self.SWING = 1
        self.HANDSTAND = 2
        self.LANDING = 3
        
        self.pose_names = {
            0: 'starting',
            1: 'swing',
            2: 'handstand',
            3: 'landing'
        }
    
    def calculate_angle(self, point1, point2, point3):
        """
        Calculate angle between three points
        
        Args:
            point1, point2, point3: Points with x, y coordinates
            
        Returns:
            Angle in degrees
        """
        a = np.array([point1.x, point1.y])
        b = np.array([point2.x, point2.y])
        c = np.array([point3.x, point3.y])
        
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
                  np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle
    
    def get_body_angle(self, landmarks):
        """
        Calculate body angle relative to vertical
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            Body angle in degrees (0 = upright, 90 = horizontal, 180 = inverted)
        """
        # Get shoulder and hip positions
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Calculate midpoints
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_mid_y = (left_hip.y + right_hip.y) / 2
        shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
        hip_mid_x = (left_hip.x + right_hip.x) / 2
        
        # Calculate angle from vertical
        dx = hip_mid_x - shoulder_mid_x
        dy = hip_mid_y - shoulder_mid_y
        
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        
        # Determine if inverted
        if shoulder_mid_y > hip_mid_y:  # Shoulders below hips = inverted
            angle = 180 - angle
            
        return angle
    
    def is_hands_on_ground(self, landmarks):
        """
        Check if hands are on the ground (wrists below hips)
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            Boolean indicating if hands are on ground
        """
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        hip_avg_y = (left_hip.y + right_hip.y) / 2
        wrist_avg_y = (left_wrist.y + right_wrist.y) / 2
        
        # Wrists significantly below hips (in image coordinates, higher y = lower position)
        return wrist_avg_y > hip_avg_y + 0.15
    
    def get_body_velocity(self, landmarks_curr, landmarks_prev):
        """
        Calculate body movement velocity between frames
        
        Args:
            landmarks_curr: Current frame landmarks
            landmarks_prev: Previous frame landmarks
            
        Returns:
            Velocity magnitude
        """
        if landmarks_prev is None:
            return 0.0
        
        # Calculate center of mass movement
        hip_curr = landmarks_curr[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        hip_prev = landmarks_prev[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        
        dx = hip_curr.x - hip_prev.x
        dy = hip_curr.y - hip_prev.y
        
        velocity = math.sqrt(dx**2 + dy**2)
        return velocity
    
    def classify_pose(self, landmarks, prev_landmarks=None):
        """
        Classify the current pose based on body angles and positions
        
        Args:
            landmarks: MediaPipe pose landmarks
            prev_landmarks: Previous frame landmarks for velocity calculation
            
        Returns:
            Pose label (0=starting, 1=swing, 2=handstand, 3=landing)
        """
        if landmarks is None:
            return None
        
        # Calculate features
        body_angle = self.get_body_angle(landmarks)
        hands_on_ground = self.is_hands_on_ground(landmarks)
        velocity = self.get_body_velocity(landmarks, prev_landmarks)
        
        # Get knee and hip angles for additional context
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        
        knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        torso_angle = self.calculate_angle(left_shoulder, left_hip, left_knee)
        
        # Classification rules
        # HANDSTAND: Inverted (body angle > 135°) with hands on ground
        if body_angle > 135 and hands_on_ground:
            return self.HANDSTAND
        
        # SWING: Significant forward lean (45-135°) or high velocity
        elif (45 < body_angle < 135) or velocity > 0.02:
            return self.SWING
        
        # STARTING: Upright position (body angle < 45°), low velocity, at beginning
        elif body_angle < 45 and velocity < 0.01 and knee_angle > 160:
            return self.STARTING
        
        # LANDING: Upright position but may have bent knees, after handstand
        elif body_angle < 45:
            return self.LANDING
        
        # Default to swing if uncertain
        return self.SWING
    
    def detect_pose_transitions(self, pose_sequence):
        """
        Detect transition frames between poses
        
        Args:
            pose_sequence: List of pose labels for each frame
            
        Returns:
            Dictionary with pose transition frames
        """
        if not pose_sequence:
            return {}
        
        transitions = {
            'starting': 0,
            'swing': None,
            'handstand': None,
            'landing': None
        }
        
        # Find first occurrence of each pose
        for i, pose in enumerate(pose_sequence):
            if pose is None:
                continue
                
            pose_name = self.pose_names[pose]
            
            # Record first occurrence of each pose
            if transitions[pose_name] is None:
                transitions[pose_name] = i
        
        # Ensure we have all poses (fill with -1 if not detected)
        for pose_name in transitions:
            if transitions[pose_name] is None:
                transitions[pose_name] = -1
        
        return transitions
    
    def process_video(self, video_path: str, show_visualization: bool = False) -> Dict:
        """
        Process a single video and detect pose transitions
        
        Args:
            video_path: Path to video file
            show_visualization: Whether to display video with pose overlay
            
        Returns:
            Dictionary with pose transition information
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return None
        
        frame_count = 0
        pose_sequence = []
        prev_landmarks = None
        
        print(f"Processing: {os.path.basename(video_path)}")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe
            results = self.pose.process(rgb_frame)
            
            # Classify pose
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                pose_label = self.classify_pose(landmarks, prev_landmarks)
                pose_sequence.append(pose_label)
                prev_landmarks = landmarks
                
                # Visualization
                if show_visualization:
                    # Draw pose landmarks with updated API
                    self.mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        self.mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                    )
                    
                    # Display pose label
                    if pose_label is not None:
                        pose_text = self.pose_names[pose_label].upper()
                        cv2.putText(frame, pose_text, (10, 50),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Display frame number
                    cv2.putText(frame, f"Frame: {frame_count}", (10, 100),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow('Pose Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            else:
                pose_sequence.append(None)
            
            frame_count += 1
        
        cap.release()
        if show_visualization:
            cv2.destroyAllWindows()
        
        # Detect transitions
        transitions = self.detect_pose_transitions(pose_sequence)
        
        result = {
            'videoname': os.path.basename(video_path),
            'starting': transitions['starting'],
            'swing': transitions['swing'],
            'handstand': transitions['handstand'],
            'landing': transitions['landing'],
            'total_frames': frame_count
        }
        
        print(f"  Detected transitions: {transitions}")
        
        return result
    
    def process_video_directory(self, directory_path: str, output_csv: str = 'pose_labels.csv', 
                                show_visualization: bool = False):
        """
        Process all .mov videos in a directory
        
        Args:
            directory_path: Path to directory containing videos
            output_csv: Output CSV file path
            show_visualization: Whether to show visualization for each video
        """
        video_dir = Path(directory_path)
        video_files = list(video_dir.glob('*.mov')) + list(video_dir.glob('*.MOV'))
        
        if not video_files:
            print(f"No .mov files found in {directory_path}")
            return
        
        print(f"Found {len(video_files)} videos to process")
        
        results = []
        
        for i, video_path in enumerate(video_files):
            print(f"\n[{i+1}/{len(video_files)}] Processing video...")
            result = self.process_video(str(video_path), show_visualization)
            
            if result:
                results.append(result)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(results)
        df = df[['videoname', 'starting', 'swing', 'handstand', 'landing']]
        df.to_csv(output_csv, index=False)
        
        print(f"\n✓ Processing complete! Results saved to {output_csv}")
        print(f"✓ Processed {len(results)} videos successfully")
        
        return df


def main():
    """
    Example usage
    """
    # Initialize labeler
    labeler = GymnasticsPoseLabeler(confidence_threshold=0.5)
    
    # Process all videos in a directory
    video_directory = "/path/to/your/videos"  # Update this path
    output_csv = "gymnastics_pose_labels.csv"
    
    # Process videos (set show_visualization=True to see the detection in real-time)
    results_df = labeler.process_video_directory(
        directory_path=video_directory,
        output_csv=output_csv,
        show_visualization=False  # Set to True to visualize
    )
    
    # Display results
    if results_df is not None:
        print("\nResults Preview:")
        print(results_df.head())


if __name__ == "__main__":
    main()