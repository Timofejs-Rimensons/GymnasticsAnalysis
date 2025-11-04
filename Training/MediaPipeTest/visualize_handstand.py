import cv2
import mediapipe as mp

from Services.handstand_phase_service import HandstandPhaseService


def visualize_handstand(video_path, output_path):
    # 1. Run your service to classify phases per frame
    service = HandstandPhaseService()
    segments, frames = service.analyze_video(video_path)

    # Map frame_idx -> phase (e.g. 0: "starting", 1: "starting", 20: "upswing", …)
    phase_per_frame = {f["frame_idx"]: f["phase"] for f in frames}

    # 2. Prepare MediaPipe drawing + video IO
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run pose model again just for visualization
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = service.pose.process(image_rgb)

        # Draw skeleton
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_styles.get_default_pose_landmarks_style()
            )

        # Get phase label for this frame
        phase = phase_per_frame.get(frame_idx, "")
        if phase:
            cv2.putText(
                frame,
                phase,
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

        # Write frame to output video
        out.write(frame)

        # (Optional) Show live window while processing
        # cv2.imshow("Handstand Analysis", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

        frame_idx += 1

    cap.release()
    out.release()
    service.close()
    cv2.destroyAllWindows()

    print(f"Saved analysed video to: {output_path}")


if __name__ == "__main__":
    input_video = r"data/input/IMG_h7.mp4"          # <- your input
    output_video = r"data/output/IMG_h7_analysis.mp4"  # <- where to save

    visualize_handstand(input_video, output_video)
