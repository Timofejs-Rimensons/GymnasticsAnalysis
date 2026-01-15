#!/usr/bin/env python3
"""
Example script to quickly test the gymnastics pose labeler
"""

from gymnastics_labeler import GymnasticsPoseLabeler
import sys
import os

def test_single_video():
    """Test with a single video"""
    print("=" * 60)
    print("SINGLE VIDEO TEST")
    print("=" * 60)
    
    video_path = input("Enter path to a single .mov video file: ").strip()
    
    if not os.path.exists(video_path):
        print(f"Error: File not found: {video_path}")
        return
    
    labeler = GymnasticsPoseLabeler(confidence_threshold=0.5)
    
    print("\nProcessing with visualization...")
    print("Press 'q' to close the window when done")
    
    result = labeler.process_video(video_path, show_visualization=True)
    
    if result:
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Video: {result['videoname']}")
        print(f"Total Frames: {result['total_frames']}")
        print(f"\nPose Transitions:")
        print(f"  Starting:  Frame {result['starting']}")
        print(f"  Swing:     Frame {result['swing']}")
        print(f"  Handstand: Frame {result['handstand']}")
        print(f"  Landing:   Frame {result['landing']}")
        
        if result['swing'] == -1 or result['handstand'] == -1 or result['landing'] == -1:
            print("\n⚠️  Warning: Some poses were not detected (-1)")
            print("   Consider adjusting confidence threshold or checking video quality")


def test_directory():
    """Test with directory of videos"""
    print("=" * 60)
    print("BATCH PROCESSING TEST")
    print("=" * 60)
    
    directory = input("Enter path to directory containing .mov videos: ").strip()
    
    if not os.path.exists(directory):
        print(f"Error: Directory not found: {directory}")
        return
    
    output_csv = input("Enter output CSV filename (default: pose_labels.csv): ").strip()
    if not output_csv:
        output_csv = "pose_labels.csv"
    
    visualize = input("Show visualization for each video? (y/n, default: n): ").strip().lower()
    show_viz = visualize == 'y'
    
    print("\nInitializing labeler...")
    labeler = GymnasticsPoseLabeler(confidence_threshold=0.5)
    
    print(f"Processing all videos in: {directory}")
    if show_viz:
        print("Press 'q' during visualization to skip to next video")
    
    df = labeler.process_video_directory(
        directory_path=directory,
        output_csv=output_csv,
        show_visualization=show_viz
    )
    
    if df is not None and len(df) > 0:
        print("\n" + "=" * 60)
        print("BATCH RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total videos processed: {len(df)}")
        print(f"Output saved to: {output_csv}")
        
        # Check for missing detections
        missing_swing = len(df[df['swing'] == -1])
        missing_handstand = len(df[df['handstand'] == -1])
        missing_landing = len(df[df['landing'] == -1])
        
        if missing_swing > 0 or missing_handstand > 0 or missing_landing > 0:
            print(f"\n⚠️  Detection Issues:")
            if missing_swing > 0:
                print(f"   - {missing_swing} videos missing swing detection")
            if missing_handstand > 0:
                print(f"   - {missing_handstand} videos missing handstand detection")
            if missing_landing > 0:
                print(f"   - {missing_landing} videos missing landing detection")
        else:
            print("\n✓ All poses detected successfully in all videos!")
        
        print(f"\nFirst 5 results:")
        print(df.head())


def main():
    """Main menu"""
    print("\n" + "=" * 60)
    print("GYMNASTICS POSE LABELER - TEST SCRIPT")
    print("=" * 60)
    print("\nThis script will help you test the automatic pose detection.")
    print("Make sure you have installed requirements: pip install -r requirements.txt")
    print("\nOptions:")
    print("1. Test with single video (with visualization)")
    print("2. Test with directory of videos (batch processing)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        test_single_video()
    elif choice == '2':
        test_directory()
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice. Please run again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()