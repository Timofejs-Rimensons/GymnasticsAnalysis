#!/usr/bin/env python3
"""
Interactive Gymnastics Pose Labeling Tool
Semi-automated labeling with manual correction capabilities

Features:
- Auto-detection suggestions from MediaPipe
- Frame-by-frame video control
- Click or keyboard to mark pose transitions
- Visual timeline overlay
- Save to CSV format

Controls:
- SPACE: Play/Pause
- LEFT/RIGHT ARROW: Previous/Next frame
- 1: Mark Starting pose
- 2: Mark Swing pose  
- 3: Mark Handstand pose
- 4: Mark Landing pose
- S: Save current labels
- Q: Quit (with save prompt)
- R: Reset all labels
- A: Toggle auto-detection overlay
"""

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
from pathlib import Path
from typing import Dict, List, Optional
import math


class InteractiveGymnasticsLabeler:
    """Interactive tool for labeling gymnastics poses with semi-automation"""
    
    def __init__(self, confidence_threshold=0.5):
        """
        Initialize the interactive labeler
        
        Args:
            confidence_threshold: Confidence threshold for MediaPipe pose detection
        """
        # MediaPipe setup with latest API
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
        
        # Pose definitions
        self.POSE_NAMES = ['starting', 'swing', 'handstand', 'landing']
        self.POSE_COLORS = {
            'starting': (0, 255, 0),    # Green
            'swing': (255, 165, 0),      # Orange  
            'handstand': (255, 0, 255),  # Magenta
            'landing': (0, 255, 255)     # Yellow
        }
        
        # State variables
        self.current_frame_idx = 0
        self.playing = False
        self.show_auto_detection = True
        
        # Labels storage
        self.manual_labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        
        self.auto_labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        
        # Video data
        self.frames = []
        self.pose_sequence = []
        self.total_frames = 0
        self.video_name = ""
        
    def calculate_angle(self, point1, point2, point3):
        """Calculate angle between three points"""
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
        """Calculate body angle relative to vertical"""
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_mid_y = (left_hip.y + right_hip.y) / 2
        shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
        hip_mid_x = (left_hip.x + right_hip.x) / 2
        
        dx = hip_mid_x - shoulder_mid_x
        dy = hip_mid_y - shoulder_mid_y
        
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        
        if shoulder_mid_y > hip_mid_y:
            angle = 180 - angle
            
        return angle
    
    def is_hands_on_ground(self, landmarks):
        """Check if hands are on ground"""
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        hip_avg_y = (left_hip.y + right_hip.y) / 2
        wrist_avg_y = (left_wrist.y + right_wrist.y) / 2
        
        return wrist_avg_y > hip_avg_y + 0.15
    
    def classify_pose(self, landmarks, prev_landmarks=None):
        """Classify pose based on body configuration"""
        if landmarks is None:
            return None
        
        body_angle = self.get_body_angle(landmarks)
        hands_on_ground = self.is_hands_on_ground(landmarks)
        
        # Simple velocity calculation
        velocity = 0.0
        if prev_landmarks:
            hip_curr = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            hip_prev = prev_landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            dx = hip_curr.x - hip_prev.x
            dy = hip_curr.y - hip_prev.y
            velocity = math.sqrt(dx**2 + dy**2)
        
        # Classification logic
        if body_angle > 135 and hands_on_ground:
            return 2  # handstand
        elif (45 < body_angle < 135) or velocity > 0.02:
            return 1  # swing
        elif body_angle < 45 and velocity < 0.01:
            return 0  # starting
        elif body_angle < 45:
            return 3  # landing
        
        return 1  # default to swing
    
    def load_video(self, video_path: str) -> bool:
        """
        Load video and perform auto-detection
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"Loading video: {os.path.basename(video_path)}")
        print(f"{'='*60}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return False
        
        self.video_name = os.path.basename(video_path)
        self.frames = []
        self.pose_sequence = []
        
        # Reset labels for new video
        self.manual_labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        self.auto_labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        
        print("Loading frames...")
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            self.frames.append(frame.copy())
            
            # Process with MediaPipe for skeleton overlay only
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                self.pose_sequence.append((None, results.pose_landmarks))
            else:
                self.pose_sequence.append((None, None))
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"  Processed {frame_count} frames...")
        
        cap.release()
        self.total_frames = len(self.frames)
        
        print(f"✓ Loaded {self.total_frames} frames")
        print(f"\nReady to label - use keys 1-4 to mark poses")
        
        return True
    
    def _detect_transitions(self):
        """Detect pose transitions from sequence"""
        pose_counts = {0: [], 1: [], 2: [], 3: []}
        
        # Collect frame indices for each pose
        for i, (pose_label, _) in enumerate(self.pose_sequence):
            if pose_label is not None:
                pose_counts[pose_label].append(i)
        
        # Find first occurrence of each pose type
        for pose_idx, pose_name in enumerate(self.POSE_NAMES):
            if pose_counts[pose_idx]:
                self.auto_labels[pose_name] = pose_counts[pose_idx][0]
            else:
                self.auto_labels[pose_name] = -1
    
    def draw_timeline(self, frame, width, height):
        """Draw timeline showing pose labels"""
        timeline_height = 60
        timeline_y = height - timeline_height
        
        # Background
        cv2.rectangle(frame, (0, timeline_y), (width, height), (50, 50, 50), -1)
        
        # Timeline bar
        bar_y = timeline_y + 10
        bar_height = 20
        cv2.rectangle(frame, (10, bar_y), (width - 10, bar_y + bar_height), (100, 100, 100), -1)
        
        # Current position indicator
        if self.total_frames > 0:
            pos_x = int(10 + (width - 20) * (self.current_frame_idx / self.total_frames))
            cv2.line(frame, (pos_x, bar_y), (pos_x, bar_y + bar_height), (255, 255, 255), 2)
        
        # Draw manual pose markers only
        for pose_name, frame_idx in self.manual_labels.items():
            if frame_idx >= 0 and self.total_frames > 0:
                marker_x = int(10 + (width - 20) * (frame_idx / self.total_frames))
                color = self.POSE_COLORS[pose_name]
                cv2.circle(frame, (marker_x, bar_y + bar_height // 2), 8, color, -1)
                cv2.circle(frame, (marker_x, bar_y + bar_height // 2), 8, (255, 255, 255), 1)
        
        # Legend
        legend_y = timeline_y + 38
        legend_x = 10
        for i, pose_name in enumerate(self.POSE_NAMES):
            color = self.POSE_COLORS[pose_name]
            cv2.circle(frame, (legend_x, legend_y), 5, color, -1)
            cv2.putText(frame, f"{i+1}:{pose_name}", (legend_x + 12, legend_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            legend_x += 120
    
    def draw_info(self, frame):
        """Draw info overlay on frame"""
        height, width = frame.shape[:2]
        
        # Frame info
        info_y = 30
        cv2.putText(frame, f"Frame: {self.current_frame_idx + 1}/{self.total_frames}", 
                   (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Current labels
        labels_y = height - 150
        cv2.putText(frame, "Current Labels:", (10, labels_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Show manual labels only
        for i, (pose_name, frame_idx) in enumerate(self.manual_labels.items()):
            y_pos = labels_y + 20 + (i * 20)
            color = self.POSE_COLORS[pose_name]
            text = f"{i+1}. {pose_name.capitalize()}: "
            text += f"Frame {frame_idx}" if frame_idx >= 0 else "Not set"
            cv2.putText(frame, text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Controls help
        help_text = [
            "SPACE: Play/Pause | ARROWS: Step | 1-4: Mark poses",
            "S: Save | N: Next video | R: Reset | Q: Quit"
        ]
        help_y = height - 90
        for i, text in enumerate(help_text):
            cv2.putText(frame, text, (10, help_y + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    
    def get_display_frame(self):
        """Get current frame with all overlays"""
        if not self.frames or self.current_frame_idx >= len(self.frames):
            return None
        
        frame = self.frames[self.current_frame_idx].copy()
        height, width = frame.shape[:2]
        
        # Draw pose landmarks if available
        if self.current_frame_idx < len(self.pose_sequence):
            _, pose_landmarks = self.pose_sequence[self.current_frame_idx]
            if pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
        
        # Draw timeline
        self.draw_timeline(frame, width, height)
        
        # Draw info
        self.draw_info(frame)
        
        return frame
    
    def mark_pose(self, pose_idx):
        """Mark current frame as a specific pose transition"""
        if 0 <= pose_idx < len(self.POSE_NAMES):
            pose_name = self.POSE_NAMES[pose_idx]
            self.manual_labels[pose_name] = self.current_frame_idx
            print(f"Marked {pose_name.capitalize()} at frame {self.current_frame_idx}")
    
    def reset_labels(self):
        """Reset all manual labels"""
        self.manual_labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        print("All labels reset")
    
    def save_labels(self, output_path: str):
        """Save labels to CSV"""
        # Always use manual labels
        data = {
            'videoname': self.video_name,
            'starting': self.manual_labels['starting'],
            'swing': self.manual_labels['swing'],
            'handstand': self.manual_labels['handstand'],
            'landing': self.manual_labels['landing']
        }
        
        # Check if file exists
        file_exists = os.path.exists(output_path)
        
        df = pd.DataFrame([data])
        df.to_csv(output_path, mode='a', header=not file_exists, index=False)
        
        print(f"\n✓ Labels saved to {output_path}")
        print(f"  {data}")
    
    def run(self, video_path: str, output_csv: str = None, batch_mode: bool = False):
        """
        Run interactive labeling session
        
        Args:
            video_path: Path to video file
            output_csv: Optional CSV output path
            batch_mode: If True, enables next video workflow
            
        Returns:
            'next' to continue to next video, 'quit' to stop, None otherwise
        """
        if not self.load_video(video_path):
            return 'quit'
        
        if output_csv is None:
            output_csv = "pose_labels.csv"
        
        window_name = "Interactive Gymnastics Labeler"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        print(f"\n{'='*60}")
        print("INTERACTIVE LABELING MODE")
        print(f"{'='*60}")
        print("\nControls:")
        print("  SPACE:       Play/Pause")
        print("  ←/→:         Previous/Next frame")
        print("  1:           Mark Starting pose")
        print("  2:           Mark Swing pose")
        print("  3:           Mark Handstand pose")
        print("  4:           Mark Landing pose")
        print("  S:           Save labels to CSV")
        if batch_mode:
            print("  N:           Save and go to Next video")
        print("  R:           Reset all labels")
        print("  Q/ESC:       Quit (with save prompt)")
        print(f"{'='*60}\n")
        
        saved_this_session = False
        
        while True:
            display_frame = self.get_display_frame()
            if display_frame is None:
                break
            
            cv2.imshow(window_name, display_frame)
            
            # Handle playback
            wait_time = 30 if self.playing else 1
            key = cv2.waitKey(wait_time) & 0xFF
            
            if key == ord(' '):  # Space: play/pause
                self.playing = not self.playing
                print("Playing" if self.playing else "Paused")
                
            elif key == 81 or key == 2:  # Left arrow: previous frame
                self.current_frame_idx = max(0, self.current_frame_idx - 1)
                self.playing = False
                
            elif key == 83 or key == 3:  # Right arrow: next frame
                self.current_frame_idx = min(self.total_frames - 1, self.current_frame_idx + 1)
                self.playing = False
                
            elif key == ord('1'):  # Mark starting
                self.mark_pose(0)
                
            elif key == ord('2'):  # Mark swing
                self.mark_pose(1)
                
            elif key == ord('3'):  # Mark handstand
                self.mark_pose(2)
                
            elif key == ord('4'):  # Mark landing
                self.mark_pose(3)
                
            elif key == ord('s') or key == ord('S'):  # Save
                self.save_labels(output_csv)
                saved_this_session = True
                if batch_mode:
                    print("\n💡 Press 'N' for next video, or continue editing")
                
            elif key == ord('n') or key == ord('N'):  # Next video (batch mode)
                if batch_mode:
                    if not saved_this_session:
                        print("\n⚠️  Saving labels before moving to next video...")
                        self.save_labels(output_csv)
                    print("\n→ Moving to next video...")
                    cv2.destroyAllWindows()
                    return 'next'
                else:
                    print("\n'N' key only works in batch mode")
                
            elif key == ord('r') or key == ord('R'):  # Reset
                self.reset_labels()
                
            elif key == ord('q') or key == ord('Q') or key == 27:  # Quit
                if batch_mode:
                    response = input("\nSave current video before quitting? (y/n): ").strip().lower()
                    if response == 'y':
                        self.save_labels(output_csv)
                else:
                    response = input("\nSave labels before quitting? (y/n): ").strip().lower()
                    if response == 'y':
                        self.save_labels(output_csv)
                cv2.destroyAllWindows()
                return 'quit'
            
            # Auto-advance frame when playing
            if self.playing:
                self.current_frame_idx += 1
                if self.current_frame_idx >= self.total_frames:
                    self.current_frame_idx = self.total_frames - 1
                    self.playing = False
                    print("Reached end of video")
        
        cv2.destroyAllWindows()
        return None


def batch_label_videos(video_directory: str, output_csv: str = "pose_labels.csv"):
    """
    Label multiple videos interactively in sequence
    
    Args:
        video_directory: Directory containing .mov videos
        output_csv: Output CSV file path
    """
    video_dir = Path(video_directory)
    video_files = sorted(list(video_dir.glob('*.mov')) + list(video_dir.glob('*.MOV')) + 
                        list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.MP4')))
    
    if not video_files:
        print(f"No video files found in {video_directory}")
        return
    
    print(f"\n{'='*60}")
    print(f"BATCH LABELING MODE")
    print(f"{'='*60}")
    print(f"Found {len(video_files)} videos to label")
    print(f"Output will be saved to: {output_csv}")
    print(f"{'='*60}\n")
    
    # Clear existing CSV if starting fresh
    response = input("Start with fresh CSV file? (y/n): ").strip().lower()
    if response == 'y' and os.path.exists(output_csv):
        os.remove(output_csv)
        print(f"Removed existing {output_csv}")
    
    labeler = InteractiveGymnasticsLabeler(confidence_threshold=0.5)
    
    for i, video_path in enumerate(video_files):
        print(f"\n{'='*60}")
        print(f"Video {i+1}/{len(video_files)}: {video_path.name}")
        print(f"{'='*60}")
        
        result = labeler.run(str(video_path), output_csv, batch_mode=True)
        
        if result == 'quit':
            print("\nBatch labeling stopped by user")
            break
        elif result == 'next':
            # Continue to next video
            continue
    
    print(f"\n{'='*60}")
    print("BATCH LABELING COMPLETE")
    print(f"{'='*60}")
    print(f"Labels saved to: {output_csv}")
    
    # Show summary
    if os.path.exists(output_csv):
        df = pd.read_csv(output_csv)
        print(f"\nTotal videos labeled: {len(df)}")
        print("\nSummary:")
        print(df.to_string(index=False))


def main():
    """Main entry point"""
    import sys
    
    print("\n" + "="*60)
    print("INTERACTIVE GYMNASTICS POSE LABELING TOOL")
    print("="*60)
    print("\nOptions:")
    print("1. Label single video")
    print("2. Batch label all videos in directory")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        video_path = input("Enter path to video file: ").strip()
        output_csv = input("Enter output CSV filename (default: pose_labels.csv): ").strip()
        if not output_csv:
            output_csv = "pose_labels.csv"
        
        labeler = InteractiveGymnasticsLabeler(confidence_threshold=0.5)
        labeler.run(video_path, output_csv)
        
    elif choice == '2':
        video_dir = input("Enter directory containing videos: ").strip()
        output_csv = input("Enter output CSV filename (default: pose_labels.csv): ").strip()
        if not output_csv:
            output_csv = "pose_labels.csv"
        
        batch_label_videos(video_dir, output_csv)
        
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
