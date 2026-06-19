// src/components/ConversationSidebar.tsx
import React, { useState, useMemo } from "react";
import { ChevronLeft, Send } from "lucide-react";
import { usePlayground } from "../context/PlaygroundContext";
import { VersionCard } from "./VersionCard";
import {
  createVersion,
  getChatVersions,
  type Version,
} from "../api/versions";

interface ConversationSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  isOpen,
  onClose,
}) => {
  const {
    selectedChat,
    // messages, // 🔥 not needed anymore
    versions,
    setVersions,
    currentVersion,
    setCurrentVersion,
    setIsLoading,
    setError,
  } = usePlayground();

  const [inputValue, setInputValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Order versions chronologically (oldest first)
  const sortedVersions = useMemo(() => {
    return [...(versions || [])].sort(
      (a, b) => a.versionNumber - b.versionNumber,
    );
  }, [versions]);

  // Submit follow-up prompt
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !selectedChat) return;

    try {
      setIsSubmitting(true);
      setIsLoading(true);

      const nextVersionNumber = (versions?.length ?? 0) + 1;

      const newVersion = await createVersion(selectedChat.id, {
        prompt: inputValue.trim(),
        versionNumber: nextVersionNumber,
      });

      const updatedVersions = await getChatVersions(selectedChat.id);
      setVersions(updatedVersions);
      setCurrentVersion(newVersion);

      setInputValue("");
    } catch (err) {
      console.error("follow-up error:", err);
      setError("Failed to submit prompt");
    } finally {
      setIsSubmitting(false);
      setIsLoading(false);
    }
  };

  const handleVersionClick = (version: Version) => {
    setCurrentVersion(version);
  };

  if (!isOpen || !selectedChat) return null;

  return (
    <aside
      className={`bg-[#0f1419] border-l border-gray-800 transition-all duration-300 flex flex-col ${
        isOpen ? "w-80" : "w-0"
      } overflow-hidden`}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Conversation</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-[#1a2332] rounded transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {sortedVersions.map((version) => (
          <div key={version.id} className="space-y-2">
            {/* USER PROMPT BUBBLE (right aligned) */}
            <div className="flex justify-end">
              <div className="max-w-[75%] rounded-2xl px-4 py-2 bg-teal-600 text-white text-sm shadow-md">
                {version.prompt}
              </div>
            </div>

            {/* AGENT MESSAGE BUBBLE (left aligned, only if present) */}
            {version.message && (
              <div className="flex justify-start">
                <div className="max-w-[75%] rounded-2xl px-4 py-2 bg-[#1e293b] text-gray-100 text-sm shadow-md">
                  {version.message}
                </div>
              </div>
            )}

            {/* VERSION CARD (unchanged) */}
            <VersionCard
              version={version}
              isActive={currentVersion?.id === version.id}
              onClick={() => handleVersionClick(version)}
            />
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-gray-800 sticky bottom-0 bg-[#0a0e14] z-20">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type a followup message..."
            disabled={isSubmitting || !selectedChat}
            className="w-full bg-[#0a0e14] border border-gray-700 rounded-full pl-4 pr-12 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-700 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isSubmitting || !selectedChat}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-teal-700 hover:bg-teal-600 rounded-full h-9 w-9 flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </form>
      </div>
    </aside>
  );
};
