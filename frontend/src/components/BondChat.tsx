"use client"

import React, { useState, useRef, useEffect } from "react"
import { MessageCircle, X, Send, Loader2, TrendingUp, ChevronDown, ChevronUp, Square } from "lucide-react"
import ReactMarkdown from "react-markdown"

// ============================================================================
// TYPES
// ============================================================================

interface ChatRecommendation {
  action: string
  name: string
  isin: string
  rationale: string
  expected_return: number
  confidence: number
  risk_score: number
  quantity: number | null
  target_price: number | null
}

interface ChatResponse {
  success: boolean
  response: string
  recommendations: ChatRecommendation[] | null
  processing_time: number
  has_analytics: boolean
  has_scores: boolean
  has_portfolio: boolean
  error: string | null
}

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  recommendations?: ChatRecommendation[]
  timestamp: Date
  isLoading?: boolean
}

interface BondChatProps {
  bondName?: string
  bondIsin?: string
}

// ============================================================================
// API CALL
// ============================================================================

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

// ============================================================================
// RECOMMENDATION CARD COMPONENT
// ============================================================================

const RecommendationCard: React.FC<{ rec: ChatRecommendation }> = ({ rec }) => {
  const actionColors: Record<string, string> = {
    BUY: "bg-green-500/20 text-green-400",
    SELL: "bg-red-500/20 text-red-400",
    HOLD: "bg-yellow-500/20 text-yellow-400",
  }

  const colorClass = actionColors[rec.action] || "bg-primary/20 text-primary"

  return (
    <div className={`flex-shrink-0 w-[200px] rounded-xl p-3 ${colorClass}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-xs px-2 py-0.5 bg-white/10 rounded">{rec.action}</span>
        <span className="text-[10px] opacity-80">
          {(rec.expected_return * 100).toFixed(1)}%
        </span>
      </div>
      <p className="text-white font-medium text-xs truncate mt-2" title={rec.name}>
        {rec.name}
      </p>
      <p className="text-white/40 text-[10px] mt-1 truncate">ISIN: {rec.isin}</p>
      {rec.target_price && (
        <p className="text-white/50 text-[10px]">Target: ₹{rec.target_price.toFixed(2)}</p>
      )}
    </div>
  )
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const BondChat: React.FC<BondChatProps> = ({ bondName, bondIsin }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [includeBondContext, setIncludeBondContext] = useState(true)
  const [showRecommendations, setShowRecommendations] = useState<Record<string, boolean>>({})
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  const toggleRecommendations = (messageId: string) => {
    setShowRecommendations(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }))
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsLoading(false)
      // Remove loading message
      setMessages(prev => prev.filter(m => !m.isLoading))
    }
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    let prompt = inputValue.trim()
    
    // Add bond context if enabled and bond info is available
    if (includeBondContext && bondName) {
      prompt = `[Context: Currently viewing bond "${bondName}"${bondIsin ? ` (ISIN: ${bondIsin})` : ""}] ${prompt}`
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    const loadingMessage: ChatMessage = {
      id: `loading-${Date.now()}`,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    }

    setMessages(prev => [...prev, userMessage, loadingMessage])
    setInputValue("")
    setIsLoading(true)

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      // Build conversation history for context
      const conversationHistory = messages
        .filter(m => !m.isLoading)
        .map(m => ({
          role: m.role,
          content: m.content,
        }))

      const response = await fetch(`${API_BASE}/bonds/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt,
          user_id: "web_user",
          conversation_history: conversationHistory,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data: ChatResponse = await response.json()

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.success ? data.response : (data.error || "Sorry, something went wrong."),
        recommendations: data.recommendations || undefined,
        timestamp: new Date(),
      }

      // Remove loading message and add actual response
      setMessages(prev => [...prev.filter(m => !m.isLoading), assistantMessage])
      
      // Auto-expand recommendations for the new message if there are any
      if (data.recommendations && data.recommendations.length > 0) {
        setShowRecommendations(prev => ({
          ...prev,
          [assistantMessage.id]: true
        }))
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Request was aborted, don't show error
        return
      }
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Failed to send message"}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev.filter(m => !m.isLoading), errorMessage])
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-primary hover:bg-primary/90 text-black rounded-full shadow-[0_4px_12px_rgba(20,184,166,0.4)] flex items-center justify-center transition-all duration-200 hover:scale-105 z-50"
          title="Chat with AI Assistant"
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(20, 184, 166, 0.5)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(20, 184, 166, 0.4)'
          }}
        >
          <MessageCircle className="w-6 h-6" />
        </button>
      )}

      {/* Chat Panel - Full Height Sidebar */}
      <>
        {/* Overlay */}
        {isOpen && (
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 transition-opacity duration-300"
            onClick={() => setIsOpen(false)}
            style={{
              opacity: isOpen ? 1 : 0,
              pointerEvents: isOpen ? 'auto' : 'none',
            }}
          />
        )}
        {/* Sidebar */}
        <div
          className="fixed top-0 right-0 w-[480px] h-screen bg-[#0d1f2d] border-l border-[#145b5b] flex flex-col z-50 overflow-hidden transition-transform duration-300 ease-out"
          style={{
            transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
            boxShadow: isOpen ? '-4px 0 24px rgba(0, 0, 0, 0.3)' : 'none',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-[#145b5b] bg-[#0d1f2d]/99 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-[15px]">Bond AI Assistant</h3>
                <p className="text-xs text-white/50">Ask about bonds & recommendations</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-white/60" />
            </button>
          </div>

          {/* Bond Context Toggle */}
          {bondName && (
            <div className="px-6 py-3 bg-white/5 border-b border-[#145b5b]/50">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeBondContext}
                  onChange={(e) => setIncludeBondContext(e.target.checked)}
                  className="w-4 h-4 rounded bg-white/10 text-primary focus:ring-primary focus:ring-offset-0 accent-primary"
                />
                <span className="text-sm text-white/60">
                  Include: <span className="text-primary font-medium">{bondName}</span>
                </span>
              </label>
            </div>
          )}

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4 custom-scrollbar">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
                  <MessageCircle className="w-8 h-8 text-primary" />
                </div>
                <h4 className="text-white font-medium mb-2">Start a conversation</h4>
                <p className="text-white/50 text-sm max-w-[280px] mb-6">
                  Ask me about bond recommendations, portfolio analysis, or market insights.
                </p>
                <div className="space-y-2 w-full">
                  <p className="text-white/30 text-xs uppercase tracking-wider">Suggestions</p>
                  {[
                    "What are the best bonds to buy today?",
                    "Recommend high yield AAA bonds",
                    "Analyze my portfolio risk",
                  ].map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputValue(suggestion)}
                      className="w-full text-left px-4 py-3 text-sm text-white/70 bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-black"
                        : "bg-white/5 text-white"
                    }`}
                  >
                    {message.isLoading ? (
                      <div className="flex items-center gap-2 py-1">
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        <span className="text-white/60 text-sm">Thinking...</span>
                      </div>
                    ) : (
                      <>
                        <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-white prose-a:text-primary">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                        
                        {/* Recommendations Section - Horizontal Scroll */}
                        {message.recommendations && message.recommendations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-white/10">
                            <button
                              onClick={() => toggleRecommendations(message.id)}
                              className="flex items-center gap-2 text-xs text-primary hover:text-primary/80 transition-colors mb-2 font-medium"
                            >
                              {showRecommendations[message.id] ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                              {message.recommendations.length} Recommendations
                            </button>
                            
                            {showRecommendations[message.id] && (
                              <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 custom-scrollbar">
                                {message.recommendations.map((rec, idx) => (
                                  <RecommendationCard key={idx} rec={rec} />
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        
                        <p className="text-[10px] opacity-40 mt-2">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="px-6 py-5 border-t border-[#145b5b] bg-[#0d1f2d]/99 backdrop-blur-sm">
            <div className="flex gap-3">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about bonds..."
                rows={1}
                disabled={isLoading}
                className="flex-1 px-4 py-3 bg-[#0b1623] border border-[#145b5b] rounded-xl text-white placeholder:text-white/30 focus:outline-none focus:border-primary resize-none text-sm transition-colors disabled:opacity-50"
                style={{ minHeight: "48px", maxHeight: "120px" }}
              />
              {isLoading ? (
                <button
                  onClick={handleStop}
                  className="px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl transition-colors flex items-center gap-2"
                  title="Stop generating"
                >
                  <Square className="w-4 h-4 fill-current" />
                </button>
              ) : (
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                  className="px-4 py-3 bg-primary hover:bg-primary/90 disabled:bg-white/10 disabled:text-white/30 disabled:cursor-not-allowed text-black rounded-xl transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </>
    </>
  )
}

export default BondChat
