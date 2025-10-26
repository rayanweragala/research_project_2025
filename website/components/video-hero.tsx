"use client";

import { useRef, useState, useEffect } from "react";
import { Play } from "lucide-react";

export function VideoHero() {
  const [isPlaying, setIsPlaying] = useState(true);
  const videoRef = useRef(null);

  const startVideo = () => {
    if (videoRef.current) {
      setIsPlaying(true);

      videoRef.current.play().catch((error) => {
        console.error("Autoplay failed:", error);
        setIsPlaying(false);
      });
    }
  };

  useEffect(() => {
    startVideo();
  }, []);

  const handlePlayVideo = () => {
    startVideo();
  };

  return (
    <div className="relative w-full h-screen bg-slate-900 overflow-hidden">
      <video
        ref={videoRef}
        className="absolute inset-0 w-full h-full object-cover"
        poster="/smart-glasses-video-thumbnail.jpg"
        controls={isPlaying}
        muted
        loop
        playsInline
      >
        <source src="/smart-glasses-demo.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      <div className="absolute inset-0 bg-black/50" />

      <div className="absolute inset-0 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl text-center space-y-6">
          {!isPlaying && (
            <button
              onClick={handlePlayVideo}
              className="mx-auto inline-flex items-center justify-center w-20 h-20 rounded-full bg-teal-500 hover:bg-teal-600 transition-colors shadow-2xl hover:shadow-teal-500/50"
              aria-label="Play video"
            >
              <Play className="w-8 h-8 text-white fill-white" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
