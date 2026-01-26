#!/usr/bin/env python3
"""
Simple example of using the analytics service directly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.HandstandAnalyticsService import HandstandAnalyticsService
import numpy as np
import json

# Load config
with open('app/config.json', 'r') as f:
    config = json.load(f)

# Initialize analytics service
analytics = HandstandAnalyticsService(config=config.get('pose_criteria', {}))

# Example: Create a sample 13-joint pose
sample_pose_13 = np.array([
    [0.0, 0.5, 0.0],   # 0: nose
    [-0.1, 0.3, 0.0],  # 1: left shoulder
    [0.1, 0.3, 0.0],   # 2: right shoulder
    [-0.15, 0.2, 0.0], # 3: left elbow
    [0.15, 0.2, 0.0],  # 4: right elbow
    [-0.2, 0.1, 0.0],  # 5: left wrist
    [0.2, 0.1, 0.0],   # 6: right wrist
    [-0.05, 0.4, 0.0], # 7: left hip
    [0.05, 0.4, 0.0],  # 8: right hip
    [-0.05, 0.6, 0.0], # 9: left knee
    [0.05, 0.6, 0.0],  # 10: right knee
    [-0.05, 0.8, 0.0], # 11: left ankle
    [0.05, 0.8, 0.0],  # 12: right ankle
])

# Analyze the handstand pose
print("Analyzing sample handstand pose...")
result = analytics.analyze_pose(sample_pose_13, 'Handstand')

print("\n" + "="*60)
print("ANALYSIS RESULTS")
print("="*60)

print(f"\nAnalytics Score: {result['score']:.2f}")

print(f"\nMeasurements:")
for key, value in result['measurements'].items():
    print(f"  {key}: {value:.3f}")

print(f"\nDetected Errors ({len(result['errors'])}):")
for i, error in enumerate(result.get('errors', []), 1):
    print(f"\n  {i}. {error['criterion'].replace('_', ' ').title()}")
    print(f"     Improvement: {error['improvement']}")

print("\n" + "="*60)
print("\nYou can use this with real pose data from MediaPipe!")
print("See test_analytics.py for a complete example with video processing.")
print("="*60 + "\n")
