import React, { useState } from "react";
import axios from "axios";

const UPLOAD_ENDPOINT = "http://localhost:8080/api/video/upload";

function VideoPost() {
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [status, setStatus] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];

    if (!selectedFile) return;

    const allowedTypes = ["video/mp4", "video/quicktime", "video/x-msvideo"];
    if (!allowedTypes.includes(selectedFile.type)) {
      setStatus("Invalid file type. Please upload .mp4, .mov, or .avi.");
      setFile(null);
      return;
    }

    const maxSize = 50 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setStatus("File is too large. Max 50MB allowed.");
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setStatus("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("");

    if (!file) {
      setStatus("Please select a valid video file first.");
      return;
    }

    const formData = new FormData();
    formData.append("video", file);

    try {
      const resp = await axios.post(UPLOAD_ENDPOINT, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        },
      });
      setStatus(resp.status === 200 ? "Video uploaded successfully!" : "Upload failed.");
    } catch (error) {
      console.error(error);
      setStatus("Error uploading video.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Video Upload</h1>

      <input type="file" accept="video/*" onChange={handleFileChange} />
      <button type="submit" disabled={!(file && name)}>
        Upload Video
      </button>

      {status && <p>{status}</p>}
    </form>
  );
}

export default VideoPost;
