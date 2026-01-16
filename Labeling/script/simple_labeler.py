#!/usr/bin/env python3
"""
Simple manual video labeler - one video at a time
Optimized for M4 Mac GPU
Label one video, save to CSV, then load the next one
"""

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
from pathlib import Path
from typing import Dict
import math
import os

# Optimize for M4 Mac - use GPU via Metal
os.environ['MEDIAPIPE_DISABLE_GPU'] = '0'  # Enable GPU
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TF logging


class SimpleVideoLabeler:
    """Simple video labeler - manual input, manual labeling, simple saving"""
    
    def __init__(self):
        """Initialize the labeler with M4 Mac GPU optimization"""
        # MediaPipe Pose - GPU is enabled via environment variable
        self.mp_pose = mp.solutions.pose
        
        print("Initializing MediaPipe Pose (M4 GPU optimized)...")
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("✓ Pose detector ready\n")
        
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Pose colors
        self.POSE_NAMES = ['starting', 'swing', 'handstand', 'landing']
        self.POSE_COLORS = {
            'starting': (0, 255, 0),    # Green
            'swing': (255, 165, 0),      # Orange  
            'handstand': (255, 0, 255),  # Magenta
            'landing': (0, 255, 255)     # Yellow
        }
        
        # State
        self.current_frame_idx = 0
        self.playing = False
        self.frames = []
        self.pose_sequence = []
        self.total_frames = 0
        self.video_name = ""
        self.labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
    
    def load_video(self, video_path: str) -> bool:
        """Load video frames"""
        if not os.path.exists(video_path):
            print(f"❌ File not found: {video_path}")
            return False
        
        print(f"\n{'='*60}")
        print(f"Loading: {os.path.basename(video_path)}")
        print(f"{'='*60}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("❌ Could not open video")
            return False
        
        self.video_name = os.path.basename(video_path)
        self.frames = []
        self.pose_sequence = []
        self.current_frame_idx = 0
        self.playing = False
        
        # Reset labels
        self.labels = {
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
            
            # Get pose landmarks for overlay
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                self.pose_sequence.append(results.pose_landmarks)
            else:
                self.pose_sequence.append(None)
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"  {frame_count} frames loaded...")
        
        cap.release()
        self.total_frames = len(self.frames)
        print(f"✓ Loaded {self.total_frames} frames\n")
        
        return True
    
    def mark_pose(self, pose_idx: int):
        """Mark current frame as pose"""
        if 0 <= pose_idx < len(self.POSE_NAMES):
            pose_name = self.POSE_NAMES[pose_idx]
            self.labels[pose_name] = self.current_frame_idx
            print(f"✓ Marked {pose_name.upper()} at frame {self.current_frame_idx}")
    
    def reset_labels(self):
        """Reset all labels"""
        self.labels = {
            'starting': -1,
            'swing': -1,
            'handstand': -1,
            'landing': -1
        }
        print("🔄 Labels reset")
    
    def save_csv(self, output_csv: str):
        """Append to CSV file"""
        data = {
            'videoname': self.video_name,
            'starting': self.labels['starting'],
            'swing': self.labels['swing'],
            'handstand': self.labels['handstand'],
            'landing': self.labels['landing']
        }
        
        file_exists = os.path.exists(output_csv)
        df = pd.DataFrame([data])
        df.to_csv(output_csv, mode='a', header=not file_exists, index=False)
        
        print(f"\n💾 Saved to {output_csv}")
        print(f"   {self.video_name}: starting={self.labels['starting']}, swing={self.labels['swing']}, handstand={self.labels['handstand']}, landing={self.labels['landing']}")
    
    def get_display_frame(self):
        """Get frame with overlays"""
        if not self.frames or self.current_frame_idx >= len(self.frames):
            return None
        
        frame = self.frames[self.current_frame_idx].copy()
        height, width = frame.shape[:2]
        
        # Draw pose landmarks
        if self.current_frame_idx < len(self.pose_sequence) and self.pose_sequence[self.current_frame_idx]:
            self.mp_drawing.draw_landmarks(
                frame,
                self.pose_sequence[self.current_frame_idx],
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
        
        # Frame counter
        cv2.putText(frame, f"Frame: {self.current_frame_idx + 1}/{self.total_frames}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Current labels
        cv2.putText(frame, "Labels:", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        for i, (pose_name, frame_idx) in enumerate(self.labels.items()):
            y = 95 + (i * 25)
            color = self.POSE_COLORS[pose_name]
            text = f"{i+1}. {pose_name}: "
            text += f"Frame {frame_idx}" if frame_idx >= 0 else "Not set"
            cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Controls
        controls = [
            "SPACE: Play/Pause  |  ←→: Step",
            "1-4: Mark poses  |  S: Save",
            "R: Reset  |  Q: Quit"
        ]
        for i, text in enumerate(controls):
            cv2.putText(frame, text, (10, height - 70 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        
        return frame
    
    def run(self, video_path: str, output_csv: str):
        """Run interactive labeling"""
        if not self.load_video(video_path):
            return False
        
        print("Controls:")
        print("  SPACE: Play/Pause")
        print("  ←/→:   Step frames")
        print("  1-4:   Mark poses (1=starting, 2=swing, 3=handstand, 4=landing)")
        print("  S:     Save to CSV")
        print("  R:     Reset labels")
        print("  Q:     Quit\n")
        
        window_name = "Label Video"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        while True:
            frame = self.get_display_frame()
            if frame is None:
                break
            
            cv2.imshow(window_name, frame)
            wait_time = 30 if self.playing else 1
            key = cv2.waitKey(wait_time) & 0xFF
            
            if key == ord(' '):  # Space
                self.playing = not self.playing
                print("▶️ Playing" if self.playing else "⏸️ Paused")
            
            elif key == 81 or key == 2:  # Left arrow
                self.current_frame_idx = max(0, self.current_frame_idx - 1)
                self.playing = False
            
            elif key == 83 or key == 3:  # Right arrow
                self.current_frame_idx = min(self.total_frames - 1, self.current_frame_idx + 1)
                self.playing = False
            
            elif key == ord('1'):
                self.mark_pose(0)
            
            elif key == ord('2'):
                self.mark_pose(1)
            
            elif key == ord('3'):
                self.mark_pose(2)
            
            elif key == ord('4'):
                self.mark_pose(3)
            
            elif key == ord('s') or key == ord('S'):
                self.save_csv(output_csv)
            
            elif key == ord('r') or key == ord('R'):
                self.reset_labels()
            
            elif key == ord('q') or key == ord('Q') or key == 27:
                response = input("\nSave before quitting? (y/n): ").strip().lower()
                if response == 'y':
                    self.save_csv(output_csv)
                break
            
            # Auto-advance
            if self.playing:
                self.current_frame_idx += 1
                if self.current_frame_idx >= self.total_frames:
                    self.current_frame_idx = self.total_frames - 1
                    self.playing = False
        
        cv2.destroyAllWindows()
        return True


def main():
    """Main entry point"""
    labeler = SimpleVideoLabeler()
    
    output_csv = "pose_labels.csv"
    
    print("\n" + "="*60)
    print("SIMPLE VIDEO LABELER")
    print("="*60)
    print(f"Output will append to: {output_csv}\n")
    
    while True:
        video_path = input("Enter video path (or 'q' to quit): ").strip()
        
        if video_path.lower() == 'q':
            print("Goodbye!")
            break
        
        if not video_path:
            print("Please enter a valid path\n")
            continue
        
        labeler.run(video_path, output_csv)
        
        print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
