import logging
import cv2
import mediapipe as mp
logging.getLogger('mediapipe').setLevel(logging.ERROR)

import numpy as np

class MediapipeSegmentationRepository:
    """
    MediaPipe Pose → normalized 3D pose pipeline with correct visualization.
    """

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

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

    def _normalize_pose(self, pose_landmarks, frame_width, frame_height):
        """
        Normalizes pose landmarks to a person-centric coordinate system.

        This method takes raw pose landmarks from MediaPipe and converts them into a
        normalized representation that is independent of the person's position and
        scale in the video frame.

        Args:
            pose_landmarks: A MediaPipe PoseLandmarks object containing the detected
                            landmarks for a single frame.
            frame_width (int): The width of the video frame.
            frame_height (int): The height of the video frame.

        Returns:
            A tuple containing:
            - normalized_pose (numpy.ndarray): A (13, 3) array of normalized
              person-centric pose landmarks.
            - mid_hip_reference (numpy.ndarray): A (2,) array representing the
              mid-hip reference point in pixel coordinates.
            - bounding_box_size (numpy.ndarray): A (2,) array representing the
              size of the bounding box around the pose.
            - min_coordinates (numpy.ndarray): A (2,) array representing the
              minimum x and y coordinates of the bounding box.
        """

        if pose_landmarks is None:
            return None, None, None, None

        # Convert to pixel coordinates
        pixel_coordinates = np.array([
            [
                landmark.x * frame_width,
                landmark.y * frame_height,
                landmark.z
            ]
            for landmark in [pose_landmarks.landmark[i] for i in self.joint_ids]
        ])

        # Mid-hip reference
        left_hip, right_hip = pixel_coordinates[7], pixel_coordinates[8]
        mid_hip_reference = (left_hip + right_hip)[:2] / 2

        shifted_coordinates = pixel_coordinates.copy()
        shifted_coordinates[:, :2] -= mid_hip_reference

        # Bounding box
        min_coordinates = shifted_coordinates[:, :2].min(axis=0)
        max_coordinates = shifted_coordinates[:, :2].max(axis=0)
        bounding_box_size = max_coordinates - min_coordinates
        bounding_box_size[bounding_box_size == 0] = 1.0

        # Normalize to [0,1]
        normalized_pose = shifted_coordinates.copy()
        normalized_pose[:, 0] = (shifted_coordinates[:, 0] - min_coordinates[0]) / bounding_box_size[0]
        normalized_pose[:, 1] = (shifted_coordinates[:, 1] - min_coordinates[1]) / bounding_box_size[1]

        # Scale normalize depth (optional but recommended)
        normalized_pose[:, 2] /= np.linalg.norm(bounding_box_size)

        return normalized_pose, mid_hip_reference, bounding_box_size, min_coordinates

    # ------------------------------------------------------------ #
    # Video processing
    # ------------------------------------------------------------ #

    def process_video(self, input_video_path):
        """
        Processes a video to extract normalized pose data for each frame.

        This method reads a video file, applies MediaPipe Pose estimation to each
        frame, normalizes the detected poses, and returns the results as both a list
        of frame-specific data and a stacked tensor.

        Args:
            input_video_path (str): The path to the input video file.

        Returns:
            A tuple containing:
            - frames (list): A list of dictionaries, where each dictionary
              contains the normalized pose data for a single frame.
            - pose_tensor (numpy.ndarray): A (T, 13, 3) tensor containing the
              stacked normalized poses for all frames, where T is the total
              number of frames.
            - mask (numpy.ndarray): A boolean array of shape (T,) indicating
              which frames were successfully processed.
        """
        video_capture = cv2.VideoCapture(input_video_path)
        if not video_capture.isOpened():
            raise IOError(f"Cannot open video: {input_video_path}")

        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frames = []
        normalized_poses = []

        # The MediaPipe Pose object is now initialized in the constructor
        # and reused for each video. Because 'static_image_mode' is False,
        # MediaPipe will attempt to track the pose between frames. When a new
        # video starts, tracking will likely fail, and the model will
        # automatically re-run person detection, effectively treating it as a
        # new stream.
        while video_capture.isOpened():
            success, frame = video_capture.read()
            if not success:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.pose.process(frame_rgb)

            normalized_pose, mid_hip_reference, bounding_box_size, min_coordinates = self._normalize_pose(
                result.pose_landmarks,
                frame_width,
                frame_height
            )

            frames.append({
                "pose_3d": normalized_pose,
                "reference": mid_hip_reference,
                "bbox_size": bounding_box_size,
                "min_xy": min_coordinates
            })

            normalized_poses.append(
                normalized_pose if normalized_pose is not None else None
            )

        video_capture.release()

        pose_tensor, mask = self._stack_tensor(normalized_poses)

        return frames, pose_tensor, mask

    # ------------------------------------------------------------ #
    # Tensor stacking
    # ------------------------------------------------------------ #

    def _stack_tensor(self, normalized_poses):
        """
        Stacks a list of normalized poses into a single tensor.

        This method converts a list of pose arrays (one for each frame) into a
        single numpy tensor, creating a mask to indicate which frames contain
        valid pose data.

        Args:
            normalized_poses (list): A list of normalized pose arrays. Each element
                                     can be a numpy array or None if no pose was
                                     detected in that frame.

        Returns:
            A tuple containing:
            - pose_tensor (numpy.ndarray): A (T, J, 3) tensor, where T is the
              number of frames and J is the number of joints.
            - mask (numpy.ndarray): A boolean array of shape (T,) indicating
              valid frames.
        """
        valid_poses = [pose for pose in normalized_poses if pose is not None]
        if not valid_poses:
            return np.array([]), np.array([])
            
        num_frames = len(normalized_poses)
        num_joints = valid_poses[0].shape[0]

        pose_tensor = np.zeros((num_frames, num_joints, 3))
        mask = np.zeros(num_frames, dtype=bool)

        for frame_index, pose in enumerate(normalized_poses):
            if pose is None:
                continue
            pose_tensor[frame_index] = pose
            mask[frame_index] = True

        return pose_tensor, mask

    def process_video_cosine_segments(self, input_video_path):
        """
        Processes a video to create a feature tensor based on cosine similarities.

        This method extends the basic video processing by calculating a set of
        features for each body segment based on its orientation relative to the
        torso, its parent segment, and gravity.

        Args:
            input_video_path (str): The path to the input video file.

        Returns:
            A tuple containing:
            - frames (list): The same list of frame data returned by `process_video`.
            - feature_tensor (numpy.ndarray): A (T, num_segments, 3) tensor
              of cosine similarity features.
            - mask (numpy.ndarray): A boolean array of shape (T,) indicating
              valid frames.
        """
        frames, pose_tensor, mask = self.process_video(input_video_path)
        if pose_tensor.shape[0] == 0:
             return frames, np.array([]), np.array([])

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

        parent_segment_map = {
            1: 0,  # L Forearm -> L Upper Arm
            3: 2,  # R Forearm -> R Upper Arm
            5: 4,  # L Shin -> L Thigh
            7: 6   # R Shin -> R Thigh
        }

        num_frames = pose_tensor.shape[0]
        num_segments = len(body_segments)
        num_features = 3  # Torso, Parent, Gravity
        
        feature_tensor = np.zeros((num_frames, num_segments, num_features))

        for frame_index in range(num_frames):
            if not mask[frame_index]:
                continue

            pose_at_frame = pose_tensor[frame_index]
            hip_midpoint = (pose_at_frame[7] + pose_at_frame[8]) / 2
            shoulder_midpoint = (pose_at_frame[1] + pose_at_frame[2]) / 2
            torso_vector = shoulder_midpoint - hip_midpoint

            gravity_vector = torso_vector.copy()
            if gravity_vector[1] > 0:
                gravity_vector = -gravity_vector
            
            torso_norm = np.linalg.norm(torso_vector)
            gravity_norm = np.linalg.norm(gravity_vector)

            if torso_norm == 0 or gravity_norm == 0:
                continue

            normalized_torso_vector = torso_vector / torso_norm
            normalized_gravity_vector = gravity_vector / gravity_norm
            
            segment_vectors = {}
            for i, (start_joint, end_joint) in enumerate(body_segments):
                vector = pose_at_frame[end_joint] - pose_at_frame[start_joint]
                norm = np.linalg.norm(vector)
                segment_vectors[i] = vector / norm if norm > 0 else np.zeros(3)

            for segment_index in range(num_segments):
                segment_vector = segment_vectors[segment_index]
                if np.all(segment_vector == 0):
                    continue

                similarity_to_torso = np.dot(segment_vector, normalized_torso_vector)

                parent_index = parent_segment_map.get(segment_index)
                similarity_to_parent = 0.0
                if parent_index is not None:
                    parent_vector = segment_vectors.get(parent_index)
                    if parent_vector is not None and not np.all(parent_vector == 0):
                        similarity_to_parent = np.dot(segment_vector, parent_vector)

                similarity_to_gravity = np.dot(segment_vector, normalized_gravity_vector)

                feature_tensor[frame_index, segment_index] = [similarity_to_torso, similarity_to_parent, similarity_to_gravity]

        return frames, feature_tensor, mask