#!/usr/bin/env python3
"""
Automated batch labeler - processes all videos automatically
Use this for quick initial labeling, then use interactive_labeler.py to review/correct
"""

from gymnastics_labeler import GymnasticsPoseLabeler
from pathlib import Path
import sys


def auto_label_all_videos(video_directory: str = "../videos", output_csv: str = "auto_labels.csv"):
    """
    Automatically label all videos in directory
    
    Args:
        video_directory: Directory containing videos
        output_csv: Output CSV file
    """
    print("\n" + "="*60)
    print("AUTOMATED BATCH LABELING")
    print("="*60)
    print("\nThis will automatically process all videos using AI detection.")
    print("Results may need manual review using interactive_labeler.py")
    print("="*60 + "\n")
    
    labeler = GymnasticsPoseLabeler(confidence_threshold=0.5)
    
    # Process all videos
    df = labeler.process_video_directory(
        directory_path=video_directory,
        output_csv=output_csv,
        show_visualization=False  # No GUI for batch processing
    )
    
    if df is not None:
        print("\n" + "="*60)
        print("AUTOMATED LABELING COMPLETE")
        print("="*60)
        print(f"\n✓ Processed {len(df)} videos")
        print(f"✓ Saved to: {output_csv}")
        
        # Show summary statistics
        print("\nDetection Summary:")
        print(f"  Videos with all poses detected: {len(df[(df['swing'] != -1) & (df['handstand'] != -1) & (df['landing'] != -1)])}")
        print(f"  Videos missing swing: {len(df[df['swing'] == -1])}")
        print(f"  Videos missing handstand: {len(df[df['handstand'] == -1])}")
        print(f"  Videos missing landing: {len(df[df['landing'] == -1])}")
        
        print("\n💡 Tip: Use interactive_labeler.py to review and correct these labels")
        print("   python interactive_labeler.py")
        
        return df
    
    return None


def main():
    """Main entry point"""
    script_dir = Path(__file__).parent
    videos_dir = script_dir.parent / "videos"
    
    if not videos_dir.exists():
        print(f"Error: Videos directory not found: {videos_dir}")
        return
    
    print(f"Video directory: {videos_dir}")
    output = input("Output CSV filename (default: auto_labels.csv): ").strip()
    if not output:
        output = "auto_labels.csv"
    
    confirm = input(f"\nProcess all .mov/.MOV files in {videos_dir}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return
    
    auto_label_all_videos(str(videos_dir), output)


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
