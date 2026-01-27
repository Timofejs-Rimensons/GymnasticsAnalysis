import cv2
import numpy as np
import subprocess
import os
from PIL import Image, ImageDraw, ImageFont


# Font cache for loaded fonts
_FONT_CACHE = {}


def _get_font(font_style, size):
    """
    Get a PIL font using system fonts. Uses modern system fonts on macOS/Linux/Windows.

    Args:
        font_style: "bold" or "regular"
        size: Font size in pixels

    Returns:
        PIL ImageFont object
    """
    cache_key = (font_style, size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    # Priority list of system fonts (ordered by preference)
    # Using modern, clean sans-serif fonts similar to DM Sans
    if font_style == "bold":
        system_fonts = [
            "/System/Library/Fonts/SFNS.ttf",  # macOS San Francisco (bold weight)
            "/System/Library/Fonts/Helvetica.ttc",  # macOS Helvetica
            "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS Helvetica Neue
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows Arial Bold
            "C:\\Windows\\Fonts\\seguisb.ttf",  # Windows Segoe UI Semibold
        ]
    else:  # regular
        system_fonts = [
            "/System/Library/Fonts/SFNS.ttf",  # macOS San Francisco
            "/System/Library/Fonts/Helvetica.ttc",  # macOS Helvetica
            "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS Helvetica Neue
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows Arial
            "C:\\Windows\\Fonts\\segoeui.ttf",  # Windows Segoe UI
        ]

    # Try each font in order
    for font_path in system_fonts:
        try:
            font = ImageFont.truetype(font_path, size)
            _FONT_CACHE[cache_key] = font
            return font
        except Exception:
            continue

    # Final fallback to PIL default (bitmap font, always works)
    font = ImageFont.load_default()
    _FONT_CACHE[cache_key] = font
    return font


def _draw_pose_on_frame(frame, frame_data, pose_label_text, is_overlay, segment_scores=None):
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
        segment_scores (dict, optional): A dictionary of scores for each segment.
                                         Defaults to None.

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

    body_segments_map = {
        (1, 3): 0, (3, 5): 1, (2, 4): 2, (4, 6): 3, (7, 9): 4,
        (9, 11): 5, (8, 10): 6, (10, 12): 7, (1, 2): 8, (7, 8): 9
    }

    for start_idx, end_idx in connections:
        color = (200, 200, 200)  # Default white
        if segment_scores:
            # The order of indices in the tuple might matter
            segment_tuple = (start_idx, end_idx)
            if segment_tuple not in body_segments_map:
                segment_tuple = (end_idx, start_idx) # Try reversed

            segment_index = body_segments_map.get(segment_tuple)
            
            if segment_index is not None:
                score = segment_scores.get(segment_index)
                if score is not None:
                    # BGR color: (blue, green, red)
                    # score 0 -> red (0, 0, 255), score 1 -> green (0, 255, 0)
                    color = (0, int(255 * score), int(255 * (1 - score)))

        cv2.line(frame, tuple(projected_points[start_idx]), tuple(projected_points[end_idx]),
                 color, 4)

    if pose_label_text:
        # Load fonts (bold for title, regular for body)
        title_font = _get_font("bold", 36)
        text_font = _get_font("regular", 26)

        # Position text on the right side
        frame_height, frame_width, _ = frame.shape
        padding = 20
        line_spacing = 45
        right_margin = 30
        y_position = 40

        # Semi-transparent dark background (RGBA: Black with 75% opacity)
        bg_color = (0, 0, 0, 190)
        text_color = (255, 255, 255)  # White text

        lines = [line for line in pose_label_text.split('\n') if line]

        # Convert OpenCV BGR to PIL RGB
        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image, 'RGBA')

        # Calculate total bounding box for all text
        max_width = 0
        total_height = 0
        line_dimensions = []

        for i, line in enumerate(lines):
            current_font = title_font if i == 0 else text_font
            bbox = draw.textbbox((0, 0), line, font=current_font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            max_width = max(max_width, line_width)
            line_dimensions.append((line_width, line_height))
            total_height += line_height + (line_spacing - line_height) if i < len(lines) - 1 else line_height

        # Calculate x_position based on actual text width, ensuring it fits on screen
        box_width = max_width + padding * 2
        # Try to position on the right, but ensure it doesn't go off screen
        x_position = max(padding, frame_width - box_width - right_margin)

        # Draw one continuous background rectangle with rounded corners for all text
        bg_rect = [
            x_position - padding,
            y_position - padding,
            x_position + max_width + padding * 2,
            y_position + total_height + padding * 2
        ]
        draw.rounded_rectangle(bg_rect, radius=12, fill=bg_color)

        # Draw all text lines (centered)
        current_y = y_position
        for i, line in enumerate(lines):
            current_font = title_font if i == 0 else text_font
            bbox = draw.textbbox((0, 0), line, font=current_font)
            line_width = bbox[2] - bbox[0]
            # Center the text horizontally within the box
            centered_x = x_position + (max_width - line_width) / 2
            draw.text((centered_x, current_y), line, font=current_font, fill=text_color)
            current_y += line_spacing

        # Convert back to OpenCV BGR
        frame = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    return frame

def save_visualized_video(output_video_path, frames, input_video_path=None, frame_annotations=None):
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
        frame_annotations (list, optional): A list of dictionaries, each containing
                                            'label' and 'segment_scores' for a frame.
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
        
    temp_output_path = f"{output_video_path}_temp.mp4"
    
    video_writer = cv2.VideoWriter(temp_output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_width, frame_height))

    for frame_index, frame_data in enumerate(frames):
        if is_overlay and video_capture.isOpened():
            success, frame = video_capture.read()
            if not success:
                break
        else:
            frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        annotation = frame_annotations[frame_index] if frame_annotations and frame_index < len(frame_annotations) else {}
        current_label = annotation.get("label", "")
        segment_scores = annotation.get("segment_scores")
        
        drawn_frame = _draw_pose_on_frame(frame, frame_data, current_label, is_overlay, segment_scores)
        
        video_writer.write(drawn_frame)

    if video_capture:
        video_capture.release()
    video_writer.release()
    
    # Convert using FFMPEG to H.264 (avc1) for browser compatibility
    try:
        subprocess.run([
            "ffmpeg", "-y", 
            "-i", temp_output_path, 
            "-vcodec", "libx264", 
            "-pix_fmt", "yuv420p", # Essential for browser compatibility
            "-acodec", "aac", 
            output_video_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Remove temp file if successful
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            
    except subprocess.CalledProcessError:
        # Fallback: if ffmpeg fails, just rename temp to output (better than nothing)
        if os.path.exists(temp_output_path):
            if os.path.exists(output_video_path):
                os.remove(output_video_path)
            os.rename(temp_output_path, output_video_path)
