import cv2
import numpy as np


def _draw_pose_on_frame(frame, frame_data, pose_label_text, is_overlay):
    """
    Draws a single pose and its labels on a video frame.

    This helper function takes a frame and the corresponding pose data to draw the
    skeleton and any associated text labels.

    Args:
        frame (np.ndarray): The video frame to draw on.
        frame_data (dict): A dictionary containing the pose data for the frame.
        pose_label_text (str): The text of the label to be drawn on the frame.
        is_overlay (bool): A flag indicating whether to overlay on the original
                           frame or draw on a black background.

    Returns:
        np.ndarray: The frame with the pose and labels drawn on it.
    """
    normalized_pose = frame_data.get("pose_3d")
    if normalized_pose is None:
        return frame

    frame_height, frame_width, _ = frame.shape
    connections = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 5), (4, 6),
                   (1, 7), (2, 8), (7, 8), (7, 9), (8, 10), (9, 11), (10, 12)]

    projected_points = normalized_pose.copy()
    if is_overlay:
        projected_points[:, 0] = (normalized_pose[:, 0] * frame_data["bbox_size"][0] +
                                  frame_data["min_xy"][0] + frame_data["reference"][0])
        projected_points[:, 1] = (normalized_pose[:, 1] * frame_data["bbox_size"][1] +
                                  frame_data["min_xy"][1] + frame_data["reference"][1])
    else:
        projected_points[:, 0] = normalized_pose[:, 0] * frame_data["bbox_size"][0] + frame_width / 2
        projected_points[:, 1] = normalized_pose[:, 1] * frame_data["bbox_size"][1] + frame_height / 2

    projected_points = projected_points[:, :2].astype(int)

    for point in projected_points:
        cv2.circle(frame, tuple(point), 6, (0, 255, 0), -1)
    for start_idx, end_idx in connections:
        cv2.line(frame, tuple(projected_points[start_idx]), tuple(projected_points[end_idx]),
                 (200, 200, 200), 4)

    if pose_label_text:
        origin = (50, 50)
        font_scale = 1
        line_height = int(font_scale * 40)
        for i, line in enumerate(pose_label_text.split('\n')):
            if not line:
                continue
            line_origin = (origin[0], origin[1] + i * line_height)
            cv2.putText(frame, line, line_origin, cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, (0, 180, 255), 3, cv2.LINE_AA)

    return frame

def save_visualized_video(output_video_path, frames, input_video_path=None, pose_labels=None):
    """
    Creates and saves a video visualizing the detected poses.

    This function reprojects the normalized poses back into the video's coordinate
    space and saves the result as a new video file. It can either overlay the
    poses on the original video or render them on a black background.

    Args:
        output_video_path (str): The path to save the output video file.
        frames (list): A list of frame data dictionaries from the segmentation
                       repository.
        input_video_path (str, optional): The path to the original input video.
                                           If provided, the poses will be
                                           overlaid on this video.
                                           Defaults to None.
        pose_labels (list, optional): A list of strings, where each string is a
                                      label for the corresponding frame.
                                      Defaults to None.
    """
    is_overlay = input_video_path is not None
    
    if is_overlay:
        video_capture = cv2.VideoCapture(input_video_path)
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    else:
        video_capture = None
        fps, frame_width, frame_height = 30, 800, 800
        
    # output_video_path = str(output_video_path)

    video_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*"avc1"), fps, (frame_width, frame_height))

    for frame_index, frame_data in enumerate(frames):
        if is_overlay and video_capture.isOpened():
            success, frame = video_capture.read()
            if not success:
                break
        else:
            frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        current_label = pose_labels[frame_index] if pose_labels and frame_index < len(pose_labels) else ""
        
        drawn_frame = _draw_pose_on_frame(frame, frame_data, current_label, is_overlay)
        
        video_writer.write(drawn_frame)

    if video_capture:
        video_capture.release()
    video_writer.release()