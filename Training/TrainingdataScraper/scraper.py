import os
import re
import csv
import shutil

import os
import re
import csv

def extract_scores_from_txt(txt_path, output_csv):
    """Extract spreidsprong (S1–S#) scores from a .txt file and write to CSV."""
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Normalize whitespace and remove redundant newlines
    text = re.sub(r"\s+", " ", text)

    # Regex pattern tuned for this file
    pattern = re.compile(
        r"(S\d+).*?Aanloop.*?(\d).*?"
        r"Afstoot.*?(\d).*?"
        r"Zweeffase 1\s*&\s*handplaatsing.*?(\d).*?"
        r"Zweeffase 2.*?(\d).*?"
        r"(?:Landing|Afwerking).*?(\d)",
        re.S | re.IGNORECASE
    )

    matches = pattern.findall(text)
    data = []
    for m in matches:
        sid, aanloop, afstoot, zweef1, zweef2, landing = m
        video_name = f"IMG_{sid.lower()}.mp4"
        data.append([video_name.lower(), aanloop, afstoot, zweef1, zweef2, landing])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Write results
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["video_name", "aanloop", "afstoot", "zweeffase_1", "zweeffase_2", "landing"])
        writer.writerows(data)

    print(f"[✔] Extracted {len(data)} records into {output_csv}")
    return {os.path.splitext(row[0])[0] for row in data}



def organize_videos(input_folder, output_folder, valid_videos):
    """Copy only videos that match the parsed IDs (e.g. IMG_h1.*)."""
    vids_folder = os.path.join(output_folder, "vids")
    csv_folder = os.path.join(output_folder, "csv")
    os.makedirs(vids_folder, exist_ok=True)
    os.makedirs(csv_folder, exist_ok=True)

    # List all video files in folder
    video_files = [f for f in os.listdir(input_folder)
                   if os.path.isfile(os.path.join(input_folder, f)) and
                   f.lower().split(".")[-1] in ["mov", "mp4", "avi", "mkv"]]

    copied = 0
    for vid in video_files:
        base_name = os.path.splitext(vid)[0].lower()
        if base_name.split()[0].lower() in valid_videos:
            dst_path = os.path.join(vids_folder, f"{base_name}.mp4")
            shutil.copy2(os.path.join(input_folder, vid), dst_path)
            print(f"Copied {vid} → {os.path.basename(dst_path)}")
            copied += 1

    print(f"[✔] {copied} videos copied to {vids_folder}")
    return csv_folder


if __name__ == "__main__":
    # === CONFIG ===
    input_txt = "dirty_data.txt"
    videos_source = "dataset/spreidsprong"
    data_folder = "clean_dataset/spreidsprong"

    # === RUN ===
    os.makedirs(data_folder, exist_ok=True)
    output_csv = os.path.join(data_folder, "csv", "beoordeling.csv")

    # Step 1: Parse text & write CSV
    valid_videos = extract_scores_from_txt(input_txt, output_csv)

    # Step 2: Copy only matching videos
    organize_videos(videos_source, data_folder, valid_videos)

    print(f"[✔] All done! Clean data in '{data_folder}/'")
