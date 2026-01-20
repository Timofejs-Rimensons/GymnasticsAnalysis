"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { formatFileSize } from "@/lib/utils";

interface VideoUploaderProps {
  onFileSelect: (files: FileList) => void;
  uploadedCount: number;
  totalSize: number;
  disabled?: boolean;
}

export function VideoUploader({
  onFileSelect,
  uploadedCount,
  totalSize,
  disabled = false,
}: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (!disabled && e.dataTransfer.files) {
      onFileSelect(e.dataTransfer.files);
    }
  };

  const handleClick = () => {
    if (!disabled) fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onFileSelect(e.target.files);
    }
  };

  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        multiple
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled}
      />
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative group cursor-pointer
          border-2 border-dashed
          p-12 min-h-[250px]
          flex flex-col items-center justify-center
          transition-all duration-200
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          ${isDragging ? "border-accent bg-accent/5" : ""}
          ${uploadedCount > 0 ? "border-accent" : "border-border"}
          ${!disabled && !isDragging && uploadedCount === 0 ? "hover:border-accent" : ""}
          bg-surface
        `}
      >
        <div
          className={`
            mb-6 p-4 border-2 transition-colors duration-200
            ${
              uploadedCount > 0
                ? "border-accent bg-accent/10"
                : isDragging
                  ? "border-accent"
                  : "border-border group-hover:border-accent"
            }
          `}
        >
          <Upload
            className={`w-10 h-10 transition-colors duration-200 ${
              uploadedCount > 0
                ? "text-accent"
                : isDragging
                  ? "text-accent"
                  : "text-muted-foreground group-hover:text-accent"
            }`}
          />
        </div>

        {uploadedCount > 0 ? (
          <div className="text-center">
            <p
              className="text-xl font-bold uppercase tracking-tight mb-2"
              style={{ fontFamily: "'Archivo Black', sans-serif" }}
            >
              {uploadedCount} VIDEO{uploadedCount > 1 ? "S" : ""} UPLOADED
            </p>
            <p className="text-sm font-mono text-muted-foreground">
              {formatFileSize(totalSize)} total
            </p>
            <p className="text-sm text-accent mt-3 font-medium">
              Click or drop to add more
            </p>
          </div>
        ) : (
          <div className="text-center">
            <p
              className="text-xl font-bold uppercase tracking-tight mb-2"
              style={{ fontFamily: "'Archivo Black', sans-serif" }}
            >
              DROP VIDEO HERE
            </p>
            <p className="text-sm text-muted-foreground">
              or click to upload / MP4, MOV, AVI
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
