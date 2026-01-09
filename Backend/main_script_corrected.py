import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
from app.services.PoseScoringService import PoseScoringService # Assuming this path is correct

base_path = Path("./temp/dataset/handstand/") # Use Path for better path manipulation
video_paths = os.listdir(base_path)
pose_names = ["starting", "swing", "landing"]
db = pd.DataFrame(columns=pose_names + ["frame"])

pose_scoring_service = PoseScoringService()
row_list = [] # Collect rows first, then concatenate

for video_file_name in tqdm(video_paths[::32]):
    full_path = base_path / video_file_name

    # Assuming get_poses_from_video returns a list of dictionaries, where each
    # dictionary represents scores for a frame.
    # e.g., [{"pose1": {"score": 0.5}, "pose2": {"score": 0.3}}, ...]
    poses_scores, _ = pose_scoring_service.get_poses_from_video(str(full_path), "handstand")

    for frame_index, score_data_for_frame in enumerate(poses_scores):
        row_dict = {}
        for pose_name in pose_names:
            # Access the 'score' from the nested dictionary, defaulting to 0 if pose_name not found
            row_dict[pose_name] = score_data_for_frame.get(pose_name, {"score": 0})["score"]
        row_dict["frame"] = frame_index
        row_list.append(row_dict)

# After the loop, concatenate all collected rows at once for efficiency
if row_list:
    db = pd.concat([db, pd.DataFrame(row_list)], ignore_index=True)

print(db.head())
