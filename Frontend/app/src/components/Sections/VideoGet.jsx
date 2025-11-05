import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import videojs from "video.js";
import styles from "./Sections.module.css";
import "video.js/dist/video-js.css";

const BASE_URL = "http://localhost:8001";

function VideoGet({ videoId }) {
  const [status, setStatus] = useState("processing");
  const [videoUrl, setVideoUrl] = useState(null);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  useEffect(() => {
    if (!videoId) return;

    let intervalId;

    const fetchStatus = async () => {
      try {
        const { data } = await axios.get(`${BASE_URL}/api/video/status/${videoId}`);
        const { status: videoStatus, url } = data;

        if (videoStatus === "ready" && url) {
          setVideoUrl(`${BASE_URL}${url}`);
          setStatus("ready");
          clearInterval(intervalId);
        } else if (videoStatus === "error") {
          setStatus("error");
          clearInterval(intervalId);
        } else {
          setStatus("processing");
        }
      } catch (err) {
        console.error("Status check failed:", err);
        setError("Failed to fetch video status.");
        setStatus("error");
        clearInterval(intervalId);
      }
    };

    fetchStatus();
    intervalId = setInterval(fetchStatus, 2000);
    return () => clearInterval(intervalId);
  }, [videoId]);

  // Initialize Video.js when videoUrl is ready
  useEffect(() => {
    if (videoUrl && videoRef.current) {
      playerRef.current = videojs(videoRef.current, {
        controls: true,
        preload: "auto",
        autoplay: false,
        fluid: false,
        width: 640,
        height: 360,
        sources: [
          {
            src: videoUrl,
            type: "video/mp4",
          },
        ],
      });

      return () => {
        if (playerRef.current) {
          playerRef.current.dispose();
        }
      };
    }
  }, [videoUrl]);

  if (status === "processing") {
    return (
      <div className={styles.videoProcessing}>
        <p>Processing...</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className={styles.videoError}>
        <p>Failed to process video</p>
      </div>
    );
  }

  if (!videoUrl) {
    return <p className={styles.preparingText}>Preparing video...</p>;
  }

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = videoUrl;
    link.download = `video_${videoId}.mp4`;
    link.click();
  };

  return (
    <div className={styles.videoContainer}>
      <div className={styles.videoWrapper}>
        <video
          ref={videoRef}
          className={`video-js vjs-big-play-centered ${styles.videoPlayer}`}
          width="640"
          height="360"
          playsInline
        />
      </div>

      <div className={styles.downloadSection}>
        <button className={styles.downloadBtn} onClick={handleDownload}>
          Download
        </button>
      </div>
    </div>
  );
}

export default VideoGet;
