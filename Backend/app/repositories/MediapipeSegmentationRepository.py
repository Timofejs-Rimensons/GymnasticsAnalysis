import mediapipe as mp
import numpy as np
import warnings
import json
import os
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '2' 


class MediapipeSegmentationRepository:
    """
    MediaPipe Pose → normalized 3D pose pipeline with correct visualization.
    """

    def __init__(self):
        self.mp_pose = mp.solutions.pose

        # Selected MediaPipe joint indices (13 joints)
        self.joint_ids = [
            0,    # nose
            11, 12,  # shoulders
            13, 14,  # elbows
            15, 16,  # wrists
            23, 24,  # hips
            25, 26,  # knees
            27, 28   # ankles
        ]

    # ------------------------------------------------------------ #
    # Core pose normalization
    # ------------------------------------------------------------ #

    def _normalize_pose(self, landmarks, frame_w, frame_h):
        """
        Returns:
            pose_3d   : (13, 3) normalized person-centric
            reference : (2,) mid-hip in pixels
            bbox_size : (2,)
            min_xy    : (2,)
        """

        if landmarks is None:
            return None, None, None, None

        # Convert to pixel coordinates
        coords = np.array([
            [
                landmarks.landmark[i].x * frame_w,
                landmarks.landmark[i].y * frame_h,
                landmarks.landmark[i].z
            ]
            for i in self.joint_ids
        ])

        # Mid-hip reference
        left_hip, right_hip = coords[7], coords[8]
        reference = (left_hip + right_hip)[:2] / 2

        coords_shifted = coords.copy()
        coords_shifted[:, :2] -= reference

        # Bounding box
        min_xy = coords_shifted[:, :2].min(axis=0)
        max_xy = coords_shifted[:, :2].max(axis=0)
        bbox_size = max_xy - min_xy
        bbox_size[bbox_size == 0] = 1.0

        # Normalize to [0,1]
        pose_3d = coords_shifted.copy()
        pose_3d[:, 0] = (coords_shifted[:, 0] - min_xy[0]) / bbox_size[0]
        pose_3d[:, 1] = (coords_shifted[:, 1] - min_xy[1]) / bbox_size[1]

        # Scale normalize depth (optional but recommended)
        pose_3d[:, 2] /= np.linalg.norm(bbox_size)

        return pose_3d, reference, bbox_size, min_xy

    # ------------------------------------------------------------ #
    # Video processing
    # ------------------------------------------------------------ #

    def process_video(self, input_video_path):
        """
        Full pipeline:
        video → list of frame dicts + (T, 13, 3) tensor
        """

        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {input_video_path}")

        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frames = []
        poses_3d = []

        with self.mp_pose.Pose(
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:
            
            i = 0
            while cap.isOpened():
                i += 1
                success, frame = cap.read()
                if not success:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(frame_rgb)

                pose_3d, ref, bbox, min_xy = self._normalize_pose(
                    result.pose_landmarks,
                    frame_w,
                    frame_h
                )

                frames.append({
                    "pose_3d": pose_3d,
                    "reference": ref,
                    "bbox_size": bbox,
                    "min_xy": min_xy
                })

                poses_3d.append(
                    pose_3d if pose_3d is not None else None
                )

        cap.release()

        tensor_3d, mask = self._stack_tensor(poses_3d)

        return frames, tensor_3d, mask

    # ------------------------------------------------------------ #
    # Tensor stacking
    # ------------------------------------------------------------ #

    def _stack_tensor(self, poses):
        valid = [p for p in poses if p is not None]
        if not valid:
            return np.array([]), np.array([])
            
        T = len(poses)
        J = valid[0].shape[0]

        tensor = np.zeros((T, J, 3))
        mask = np.zeros(T, dtype=bool)

        for t, p in enumerate(poses):
            if p is None:
                continue
            tensor[t] = p
            mask[t] = True

        return tensor, mask

    def process_video_cosine_segments(self, input_video_path):
        """
        Processes a video to create a rich feature tensor based on cosine similarities.

        For each body segment, it calculates a feature vector of size 3:
        1. Similarity to the global torso vector.
        2. Similarity to the local parent segment (capturing joint angles).
        3. Similarity to a gravity-aligned "up" vector.

        Returns:
            feature_tensor: (T, num_segments, 3)
            mask          : (T,)
        """
        frames, tensor_3d, mask = self.process_video(input_video_path)
        if tensor_3d.shape[0] == 0:
             return np.array([]), np.array([])

        # Segments are defined by the indices of the joints in the `pose_3d` tensor.
        body_segments = [
            (1, 3),   # 0: L Upper Arm (shoulder to elbow)
            (3, 5),   # 1: L Forearm (elbow to wrist)
            (2, 4),   # 2: R Upper Arm (shoulder to elbow)
            (4, 6),   # 3: R Forearm (elbow to wrist)
            (7, 9),   # 4: L Thigh (hip to knee)
            (9, 11),  # 5: L Shin (knee to ankle)
            (8, 10),  # 6: R Thigh (hip to knee)
            (10, 12), # 7: R Shin (knee to ankle)
            (1, 2),   # 8: Shoulder Line
            (7, 8)    # 9: Hip Line
        ]

        # Maps a child segment to its parent to calculate joint angles.
        # E.g., The parent of the Left Forearm (1) is the Left Upper Arm (0).
        parent_segment_map = {
            1: 0,  # L Forearm -> L Upper Arm
            3: 2,  # R Forearm -> R Upper Arm
            5: 4,  # L Shin -> L Thigh
            7: 6   # R Shin -> R Thigh
        }

        num_frames = tensor_3d.shape[0]
        num_segments = len(body_segments)
        num_features = 3  # Torso, Parent, Gravity
        
        feature_tensor = np.zeros((num_frames, num_segments, num_features))

        for t in range(num_frames):
            if not mask[t]:
                continue

            pose_at_frame_t = tensor_3d[t]
            # 1. Torso Vector (Global Reference)
            hip_midpoint = (pose_at_frame_t[7] + pose_at_frame_t[8]) / 2
            shoulder_midpoint = (pose_at_frame_t[1] + pose_at_frame_t[2]) / 2
            torso_vector = shoulder_midpoint - hip_midpoint

            # 2. Gravity Vector (Person-centric "Up")
            gravity_vector = torso_vector.copy()
            if gravity_vector[1] > 0:
                gravity_vector = -gravity_vector
            
            torso_norm = np.linalg.norm(torso_vector)
            gravity_norm = np.linalg.norm(gravity_vector)

            if torso_norm == 0 or gravity_norm == 0:
                continue

            normalized_torso_vector = torso_vector / torso_norm
            normalized_gravity_vector = gravity_vector / gravity_norm
            
            # --- Pre-calculate all segment vectors for the frame ---
            segment_vectors = {}
            for i, (start_joint, end_joint) in enumerate(body_segments):
                vector = pose_at_frame_t[end_joint] - pose_at_frame_t[start_joint]
                norm = np.linalg.norm(vector)
                segment_vectors[i] = vector / norm if norm > 0 else np.zeros(3)

            # --- Calculate Feature Vector for Each Segment ---
            for i in range(num_segments):
                segment_vector = segment_vectors[i]
                if np.all(segment_vector == 0):
                    continue

                # Feature 1: Similarity to Torso
                sim_to_torso = np.dot(segment_vector, normalized_torso_vector)

                # Feature 2: Similarity to Parent (Joint Angle)
                parent_index = parent_segment_map.get(i)
                sim_to_parent = 0.0 # Default if no parent
                if parent_index is not None:
                    parent_vector = segment_vectors.get(parent_index)
                    if parent_vector is not None and not np.all(parent_vector == 0):
                        sim_to_parent = np.dot(segment_vector, parent_vector)

                # Feature 3: Similarity to Gravity
                sim_to_gravity = np.dot(segment_vector, normalized_gravity_vector)

                feature_tensor[t, i] = [sim_to_torso, sim_to_parent, sim_to_gravity]

        return feature_tensor, mask