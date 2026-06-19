"use client"

import { useState, useRef, useEffect } from "react"
import type { DailyBriefing as DailyBriefingType } from "../data/news"
import { Play, Pause, Volume2, VolumeX, Loader2, AlertCircle, X, Maximize2, Subtitles } from "lucide-react"

interface DailyBriefingProps {
  briefing: DailyBriefingType
  videoUrl?: string | null
  videoStatus?: "pending" | "generating" | "completed" | "failed"
  onPlay?: () => void
}

// Get base URL for captions
const CAPTIONS_BASE_URL = import.meta.env.VITE_VIDEO_API_URL || 
  (import.meta.env.DEV ? "http://localhost:8000" : "");

export function DailyBriefing({ briefing, videoUrl, videoStatus = "completed", onPlay }: DailyBriefingProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [showVideo, setShowVideo] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [captionsEnabled, setCaptionsEnabled] = useState(true)
  const videoRef = useRef<HTMLVideoElement>(null)

  // Handle escape key to close fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false)
      }
    }
    
    if (isFullscreen) {
      document.addEventListener("keydown", handleEscape)
      document.body.style.overflow = "hidden"
    }
    
    return () => {
      document.removeEventListener("keydown", handleEscape)
      document.body.style.overflow = ""
    }
  }, [isFullscreen])

  const handlePlay = () => {
    if (videoUrl && videoStatus === "completed") {
      setShowVideo(true)
      setIsPlaying(true)
      setIsFullscreen(true)
      setTimeout(() => {
        videoRef.current?.play()
      }, 100)
    }
    onPlay?.()
  }

  const handleVideoClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleMuteToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleCaptionsToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setCaptionsEnabled(!captionsEnabled)
    if (videoRef.current && videoRef.current.textTracks.length > 0) {
      videoRef.current.textTracks[0].mode = captionsEnabled ? "hidden" : "showing"
    }
  }

  const handleCloseFullscreen = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsFullscreen(false)
    if (videoRef.current) {
      videoRef.current.pause()
      setIsPlaying(false)
    }
  }

  const handleVideoEnd = () => {
    setIsPlaying(false)
    setIsFullscreen(false)
    setShowVideo(false)
  }

  const isLoading = videoStatus === "generating" || videoStatus === "pending"
  const hasFailed = videoStatus === "failed"
  const canPlay = videoUrl && videoStatus === "completed"

  return (
    <>
      {/* Fullscreen Video Modal */}
      {isFullscreen && showVideo && videoUrl && (
        <div 
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={handleVideoClick}
        >
          {/* Close Button */}
          <button
            className="absolute top-4 right-4 z-10 p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            onClick={handleCloseFullscreen}
          >
            <X className="w-6 h-6 text-white" />
          </button>

          {/* Volume Control */}
          <button
            className="absolute top-4 right-20 z-10 p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            onClick={handleMuteToggle}
          >
            {isMuted ? (
              <VolumeX className="w-6 h-6 text-white" />
            ) : (
              <Volume2 className="w-6 h-6 text-white" />
            )}
          </button>

          {/* Captions Toggle */}
          {briefing.captionsUrl && (
            <button
              className={`absolute top-4 right-36 z-10 p-3 rounded-full transition-colors ${
                captionsEnabled ? "bg-primary/80 hover:bg-primary" : "bg-white/10 hover:bg-white/20"
              }`}
              onClick={handleCaptionsToggle}
              title={captionsEnabled ? "Disable captions" : "Enable captions"}
            >
              <Subtitles className="w-6 h-6 text-white" />
            </button>
          )}

          {/* Video */}
          <video
            ref={videoRef}
            src={videoUrl}
            className="max-w-full max-h-full w-auto h-auto"
            onEnded={handleVideoEnd}
            onPause={() => setIsPlaying(false)}
            onPlay={() => setIsPlaying(true)}
            crossOrigin="anonymous"
          >
            {briefing.captionsUrl && (
              <track
                kind="captions"
                src={`${CAPTIONS_BASE_URL}${briefing.captionsUrl}`}
                srcLang="en"
                label="English"
                default={captionsEnabled}
              />
            )}
          </video>

          {/* Play/Pause Overlay */}
          <div className={`absolute inset-0 flex items-center justify-center pointer-events-none transition-opacity duration-300 ${isPlaying ? "opacity-0" : "opacity-100"}`}>
            <div className="w-20 h-20 bg-primary/80 rounded-full flex items-center justify-center">
              <Play className="w-10 h-10 text-white fill-white ml-1" />
            </div>
          </div>

          {/* Title at bottom */}
          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
            <h3 className="text-white text-xl font-semibold">{briefing.title}</h3>
            <p className="text-white/70">{briefing.subtitle}</p>
          </div>
        </div>
      )}

      {/* Thumbnail Card */}
      <div
        className={`relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300
          ${isHovered ? "shadow-xl shadow-primary/20 scale-[1.02]" : ""}`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={handlePlay}
      >
        {/* Thumbnail */}
        <img
          src={briefing.thumbnailUrl || "/placeholder.svg"}
          alt={briefing.title}
          className={`w-full h-44 object-cover transition-transform duration-700 ${isHovered ? "scale-110" : ""}`}
        />
        <div
          className={`absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent transition-opacity duration-300 ${isHovered ? "opacity-90" : ""}`}
        />

        {/* Play/Pause Button */}
        <div className="absolute inset-0 flex items-center justify-center">
          {isLoading ? (
            <div className="w-14 h-14 bg-white/10 rounded-full flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-white animate-spin" />
            </div>
          ) : hasFailed ? (
            <div className="w-14 h-14 bg-red-700 rounded-full flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-white" />
            </div>
          ) : (
            <button
              className={`w-14 h-14 bg-primary rounded-full flex items-center justify-center transition-all duration-300
                hover:bg-primary/80 hover:scale-110
                ${!canPlay ? "bg-white/20 cursor-not-allowed" : ""}`}
              disabled={!canPlay}
            >
              <Play className="w-6 h-6 text-white fill-white ml-1" />
            </button>
          )}
        </div>

        {/* Expand Icon */}
        {canPlay && (
          <div
            className={`absolute top-3 right-3 p-2 rounded-full bg-black/50 transition-all duration-300 ${
              isHovered ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2"
            }`}
          >
            <Maximize2 className="w-4 h-4 text-white" />
          </div>
        )}

        {/* Status Badge */}
        {isLoading && (
          <div className="absolute top-3 left-3 px-2 py-1 rounded-full bg-yellow-500/80 text-xs text-white font-medium">
            Generating...
          </div>
        )}
        {hasFailed && (
          <div className="absolute top-3 left-3 px-2 py-1 rounded-full bg-red-500/80 text-xs text-white font-medium">
            Generation failed
          </div>
        )}

        {/* Title/Subtitle */}
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <h3 className="text-white font-semibold">{briefing.title}</h3>
          <p className="text-white/70 text-sm">{briefing.subtitle}</p>
        </div>
      </div>
    </>
  )
}
