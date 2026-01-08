import cv2
import numpy as np

class VisualisationService:

    @staticmethod
    def _draw_pose_on_frame(frame, frame_data, pose_label_text, is_overlay):
        """A modular helper function to draw a single pose and its labels on a frame."""
        pose_3d = frame_data.get("pose_3d")
        if pose_3d is None: return frame

        h, w, _ = frame.shape
        connections = [(0,1),(0,2),(1,2),(1,3),(2,4),(3,5),(4,6),(1,7),(2,8),(7,8),(7,9),(8,10),(9,11),(10,12)]
        
        # --- Reproject coordinates based on context (overlay vs. black background) ---
        projected_points = pose_3d.copy()
        if is_overlay:
            projected_points[:, 0] = (pose_3d[:, 0] * frame_data["bbox_size"][0] + frame_data["min_xy"][0] + frame_data["reference"][0])
            projected_points[:, 1] = (pose_3d[:, 1] * frame_data["bbox_size"][1] + frame_data["min_xy"][1] + frame_data["reference"][1])
        else: # Center on black canvas
            projected_points[:, 0] = pose_3d[:, 0] * frame_data["bbox_size"][0] + w / 2
            projected_points[:, 1] = pose_3d[:, 1] * frame_data["bbox_size"][1] + h / 2
        
        projected_points = projected_points[:, :2].astype(int)

        # --- Draw the skeleton ---
        for point in projected_points:
            cv2.circle(frame, tuple(point), 6, (0, 255, 0), -1)
        for start_idx, end_idx in connections:
            cv2.line(frame, tuple(projected_points[start_idx]), tuple(projected_points[end_idx]), (200, 200, 200), 4)

        # --- Draw multi-line text label ---
        if pose_label_text:
            origin = (50, 50) # Top-left corner for text
            font_scale = 1
            line_height = int(font_scale * 40)
            for i, line in enumerate(pose_label_text.split('\n')):
                if not line:
                    continue
                line_origin = (origin[0], origin[1] + i * line_height)
                cv2.putText(frame, line, line_origin, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 180, 255), 3, cv2.LINE_AA)
        
        return frame

    @staticmethod
    def save_visualized_video(output_video_path, frames, input_video_path=None, pose_labels=None):
        """
        Reprojects normalized poses back to image space and saves them as a video.
        - If input_video_path is provided, it overlays the pose on the original video.
        - Otherwise, it renders the pose on a black background.
        """
        is_overlay = input_video_path is not None
        
        # --- Setup Video Writer ---
        if is_overlay:
            cap = cv2.VideoCapture(input_video_path)
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else: # Black background
            cap = None
            fps, w, h = 30, 800, 800

        out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

        # --- Process and Draw Frame by Frame ---
        for idx, frame_data in enumerate(frames):
            # Get the base frame
            if is_overlay and cap.isOpened():
                success, frame = cap.read()
                if not success: break
            else:
                frame = np.zeros((h, w, 3), dtype=np.uint8)
            
            # Get the label for the current frame
            current_label = pose_labels[idx] if pose_labels and idx < len(pose_labels) else ""
            
            # Draw the pose and labels on the frame using the helper
            drawn_frame = VisualisationService._draw_pose_on_frame(frame, frame_data, current_label, is_overlay)
            
            out.write(drawn_frame)

        if cap: cap.release()
        out.release()