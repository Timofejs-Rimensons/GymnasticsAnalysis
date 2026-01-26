#!/usr/bin/env python3
"""
Test script for analyzing gymnastics videos with pose analytics.

Usage:
    python test_analytics.py <path_to_video> [exercise_name]

Example:
    python test_analytics.py straddle_jump_video.mp4
    python test_analytics.py straddle_jump_video.mp4 straddle_jump
"""

import sys
import os
import json
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.ProcessingPipelineService import ProcessingPipelineService

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_analytics.py <path_to_video> [exercise_name]")
        print("\nExample:")
        print("  python test_analytics.py straddle_jump_video.mp4")
        print("  python test_analytics.py straddle_jump_video.mp4 straddle_jump")
        sys.exit(1)

    # Change to app directory so config.json can be found
    app_dir = os.path.join(os.path.dirname(__file__), 'app')
    os.chdir(app_dir)

    # Get input video path
    input_video_path = os.path.abspath(sys.argv[1])

    if not os.path.exists(input_video_path):
        print(f"Error: Video file not found: {input_video_path}")
        sys.exit(1)

    # Get exercise name (default to 'straddle_jump')
    exercise_name = sys.argv[2] if len(sys.argv) > 2 else 'straddle_jump'

    # Create output directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = Path(backend_dir) / "test_output"
    output_dir.mkdir(exist_ok=True)

    # Generate output file paths
    video_name = Path(input_video_path).stem
    output_video_path = str(output_dir / f"{video_name}_analyzed.mp4")
    output_json_path = str(output_dir / f"{video_name}_results.json")
    output_pdf_path = str(output_dir / f"{video_name}_report.pdf")
    status_json_path = str(output_dir / f"{video_name}_status.json")

    print(f"\n{'='*60}")
    print(f"Gymnastics Video Analysis with Pose Analytics")
    print(f"{'='*60}")
    print(f"\nInput Video:     {input_video_path}")
    print(f"Exercise:        {exercise_name}")
    print(f"Output Directory: {output_dir}")
    print(f"\n{'='*60}\n")

    try:
        # Initialize processing pipeline
        print("Initializing processing pipeline...")
        pipeline = ProcessingPipelineService()

        # Process the video
        print("Processing video... (this may take a while)")
        pipeline.analyze_video(
            input_video_path=input_video_path,
            output_video_path=output_video_path,
            output_pdf_path=output_pdf_path,
            output_json_path=output_json_path,
            exercise_name=exercise_name,
            status_json_path=status_json_path
        )

        print(f"\n{'='*60}")
        print("Analysis Complete!")
        print(f"{'='*60}\n")

        # Display results
        if os.path.exists(output_json_path):
            with open(output_json_path, 'r') as f:
                results = json.load(f)

            print("OVERALL RESULTS:")
            print(f"  Overall Score: {results.get('overall_score', 0)}/{results.get('max_score', 100)}")
            print(f"  Percentage: {results.get('percentage', 0):.1f}%")
            print()

            # Display per-pose results
            for category in results.get('categories', []):
                for pose in category.get('poses', []):
                    print(f"\n{pose['name'].upper()}:")
                    print(f"  Score: {pose['score']}/{pose['max_score']}")
                    print(f"  Description: {pose['description']}")
                    print(f"  Improvement Needed: {'Yes' if pose['improvement_needed'] else 'No'}")

                    # Display errors with analytics
                    errors = pose.get('errors', [])
                    if errors:
                        print(f"\n  Detected Issues ({len(errors)}):")
                        for idx, error in enumerate(errors, 1):
                            severity = error.get('severity', 'medium').upper()

                            print(f"    {idx}. [{severity}] {error.get('criterion', 'Unknown').replace('_', ' ').title()}")
                            print(f"       Measurement: {error.get('measurement', 'N/A')}")
                            print(f"       Frequency: {error.get('frequency', 0)*100:.0f}% of frames")
                            print(f"       Tip: {error.get('improvement', 'No suggestion available')}")
                    else:
                        print("  No issues detected!")

            print(f"\n{'='*60}")
            print("OUTPUT FILES:")
            print(f"{'='*60}")
            print(f"  Annotated Video: {output_video_path}")
            print(f"  JSON Results:    {output_json_path}")
            print(f"  PDF Report:      {output_pdf_path}")
            print(f"\n{'='*60}\n")
        else:
            print("Warning: Results JSON not found. Check for errors.")

    except Exception as e:
        print(f"\nError during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
