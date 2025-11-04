from Services.handstand_phase_service import HandstandPhaseService

def main():
    video_path = r"data/input/IMG_h7.mp4"  # relative to project root

    service = HandstandPhaseService()
    segments, frames = service.analyze_video(video_path)

    print(f"\nVideo: {video_path}")
    print("Detected segments:\n")
    for seg in segments:
        print(
            f"{seg['phase']:18s} | "
            f"{seg['start_time']:.2f}s -> {seg['end_time']:.2f}s "
            f"(frames {seg['start_frame']}–{seg['end_frame']})"
        )

    service.close()

if __name__ == "__main__":
    main()
