"use client"

import { useState, useEffect } from "react"

interface Video {
  id: string
  title: string
  description: string
  src: string
}

const videos: Video[] = [
  {
    id: "1",
    title: "System Overview",
    description: "Complete architecture and workflow demonstration",
    src: "/system-overview.mp4",
  },
]

export default function VideoSlider() {
  const [currentIndex, setCurrentIndex] = useState(() => Math.floor(Math.random() * videos.length))

  useEffect(() => {
    if (videos.length <= 1) return 

    const interval = setInterval(() => {
      let nextIndex = Math.floor(Math.random() * videos.length)
      if (nextIndex === currentIndex) {
        nextIndex = (currentIndex + 1) % videos.length 
      }
      setCurrentIndex(nextIndex)
    }, 8000)
    return () => clearInterval(interval)
  }, [currentIndex]) 

  const currentVideo = videos[currentIndex]

  return (
    <div className="relative w-full h-96 md:h-[500px] bg-slate-900 rounded-2xl overflow-hidden">
      <div className="relative w-full h-full">
        <video
          key={currentVideo.id}
          className="w-full h-full object-cover"
          poster={`/placeholder.svg?height=500&width=900&query=${currentVideo.title}`}
          autoPlay
          loop
          muted
          playsInline
        >
          <source src={currentVideo.src} type="video/mp4" />
        </video>

        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />

        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-8">
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">{currentVideo.title}</h3>
          <p className="text-teal-100 text-sm md:text-base">{currentVideo.description}</p>
        </div>
      </div>
      {videos.length > 1 && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 z-10">
          {videos.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index)}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                index === currentIndex ? "bg-teal-500 w-8" : "bg-white/50 hover:bg-white/75"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  )
}
