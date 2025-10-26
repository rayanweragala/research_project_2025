"use client"

import { useState } from "react"
import { Play } from "lucide-react"

interface VideoShowcaseProps {
  videoUrl: string
  thumbnailUrl: string
  title: string
  description?: string
}

export function VideoShowcase({ videoUrl, thumbnailUrl, title, description }: VideoShowcaseProps) {
  const [isPlaying, setIsPlaying] = useState(false)

  return (
    <div className="w-full space-y-4">
      <div className="relative w-full bg-black rounded-lg overflow-hidden aspect-video">
        {!isPlaying ? (
          <>
            <img src={thumbnailUrl || "/placeholder.svg"} alt={title} className="w-full h-full object-cover" />
            <button
              onClick={() => setIsPlaying(true)}
              className="absolute inset-0 flex items-center justify-center bg-black/40 hover:bg-black/50 transition-colors group"
              aria-label="Play video"
            >
              <div className="bg-accent text-accent-foreground p-4 rounded-full group-hover:scale-110 transition-transform">
                <Play size={32} fill="currentColor" />
              </div>
            </button>
          </>
        ) : (
          <iframe
            src={videoUrl}
            title={title}
            className="w-full h-full"
            allowFullScreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          />
        )}
      </div>
      <div>
        <h3 className="text-xl font-semibold text-foreground">{title}</h3>
        {description && <p className="text-muted-foreground mt-2">{description}</p>}
      </div>
    </div>
  )
}
