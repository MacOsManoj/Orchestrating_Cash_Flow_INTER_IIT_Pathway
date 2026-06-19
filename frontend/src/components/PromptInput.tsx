// src/components/PromptInput.tsx
import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { createVersion, getChatVersions } from '../api/versions';
import { createChat } from '../api/chats';
import { usePlayground } from '../context/PlaygroundContext';

export const PromptInput: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    setChats,
    setSelectedChat,
    setVersions,
    setCurrentVersion,
    setIsLoading,
    setError,
  } = usePlayground();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim()) return;

    try {
      setIsSubmitting(true);
      setIsLoading(true);

      const title = inputValue.trim().substring(0, 50);

      // 1. Create new chat
      const newChat = await createChat({ title });
      if (!newChat.id) {
        throw new Error('Failed to create chat: no ID returned');
      }

      // Add chat to sidebar list & select it
      setChats((prev) => [newChat, ...prev]);
      setSelectedChat(newChat);

      // 2. Create first version for this chat
      const newVersion = await createVersion(newChat.id, {
        prompt: inputValue.trim(),
        versionNumber: 1,
      });

      // 3. Load versions list (for version sidebar)
      const versions = await getChatVersions(newChat.id);
      setVersions(versions);

      // 4. Set current version (canvas will render this)
      setCurrentVersion(newVersion);

      // 5. Clear input
      setInputValue('');
    } catch (err) {
      console.error('Submit error:', err);
      setError(
        err instanceof Error ? err.message : 'Failed to create playground',
      );
    } finally {
      setIsSubmitting(false);
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center gap-3 bg-[#1a2332] rounded-full px-4 py-3 border border-[#2a3a4a]">
          {/* <button
            type="button"
            className="flex-shrink-0 p-1 hover:bg-[#2a3a4a] rounded-full transition-colors"
          >
            <Plus className="w-5 h-5 text-gray-400" />
          </button> */}

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Explore with Playground"
            disabled={isSubmitting}
            className="flex-1 bg-transparent outline-none text-sm text-white placeholder-gray-500 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!inputValue.trim() || isSubmitting}
            className="flex-shrink-0 p-2 bg-[#2e6d6d] hover:bg-[#367878] rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
