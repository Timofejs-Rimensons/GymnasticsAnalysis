#!/usr/bin/env python3
"""
Quick test script for the interactive labeler
Tests on one video from the videos directory
"""

import os
import sys
from pathlib import Path
from interactive_labeler import InteractiveGymnasticsLabeler, batch_label_videos


def test_single_video():
    """Test with first available video"""
    # Get videos directory (parent of script directory)
    script_dir = Path(__file__).parent
    videos_dir = script_dir.parent / "videos"
    
    # Find first .MOV or .mov file
    video_files = sorted(list(videos_dir.glob('*.mov')) + list(videos_dir.glob('*.MOV')))
    
    if not video_files:
        print("No video files found in videos directory")
        return
    
    test_video = video_files[0]
    print(f"Testing with: {test_video.name}")
    
    # Create labeler and run
    labeler = InteractiveGymnasticsLabeler(confidence_threshold=0.5)
    labeler.run(str(test_video), "test_labels.csv")
    
    print("\n✓ Test complete!")
    print("Check test_labels.csv for output")


def test_batch_mode():
    """Test batch labeling mode"""
    script_dir = Path(__file__).parent
    videos_dir = script_dir.parent / "videos"
    
    if not videos_dir.exists():
        print(f"Videos directory not found: {videos_dir}")
        return
    
    batch_label_videos(str(videos_dir), "gymnastics_labels.csv")


def main():
    print("\n" + "="*60)
    print("INTERACTIVE LABELER TEST")
    print("="*60)
    print("\nTest Options:")
    print("1. Test with single video (quick test)")
    print("2. Test batch mode (all 74 videos)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        test_single_video()
    elif choice == '2':
        test_batch_mode()
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
