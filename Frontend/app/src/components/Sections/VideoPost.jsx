import React, { useState } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import styles from "./Sections.module.css";
import VideoGet from "./VideoGet";

const POST_ENDPOINT = "http://localhost:8001/api/video/upload";

function VideoPost() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hover, setHover] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [uploadedVideos, setUploadedVideos] = useState([]);
  const [status, setStatus] = useState("");

  const onHover = () => setHover(true);
  const onLeave = () => setHover(false);
  const onMove = (e) => setMousePos({ x: e.clientX, y: e.clientY });

  const handleFileChange = async (e) => {
    const selectedFiles = Array.from(e.target.files).slice(0, 50);
    if (selectedFiles.length === 0) return;

    setFiles(selectedFiles);
    setLoading(true);
    setStatus("");

    try {
      const newUploads = [];

      for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append("file", selectedFiles[i]);

        const resp = await axios.post(POST_ENDPOINT, formData, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 10000,
        });

        if (resp.status !== 200) {
          throw new Error(`Upload failed for ${selectedFiles[i].name}`);
        }

        const { videoId } = resp.data;
        newUploads.push({ name: selectedFiles[i].name, videoId });
      }

      setUploadedVideos((prev) => [...prev, ...newUploads]);
      setStatus("All videos uploaded successfully!");
    } catch (err) {
      console.error(err);
      setStatus(`Upload stopped: ${err.message}`);
    } finally {
      setLoading(false);
      setFiles([]);
      e.target.value = "";
    }
  };

  return (
    <>
      <div className={styles.buttonGroup}>
        <input
          accept="video/*"
          id="contained-button-file"
          type="file"
          className={styles.hiddenFileInput}
          onChange={handleFileChange}
          multiple
          disabled={loading}
        />
        <label htmlFor="contained-button-file">
          <Button
            variant="contained"
            component="span"
            className={styles.uploadButton}
            onMouseEnter={onHover}
            onMouseLeave={onLeave}
            onMouseMove={onMove}
          >
            {loading ? "Uploading..." : "Choose Videos"}
          </Button>
        </label>

        {status && (
          <p
            className={`${styles.statusMessage} ${
              status.includes("successfully")
                ? styles.statusSuccess
                : styles.statusError
            }`}
          >
            {status}
          </p>
        )}
      </div>

      <div className={styles.videoUploadForm}>
        <div className={styles.videoSection}>
          {uploadedVideos.map((video) => (
            <div key={video.videoId} className={styles.videoItem}>
              <VideoGet videoId={video.videoId} />
              <h3 className={styles.videoName}>{video.name}</h3>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default VideoPost;
