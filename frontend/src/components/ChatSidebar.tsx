// src/components/ChatSidebar.tsx
import React from 'react';
import { ChevronLeft, MessageSquarePlus, Search } from 'lucide-react';
import { usePlayground } from '../context/PlaygroundContext';
import { type Chat } from '../api/chats';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  isOpen,
  onClose,
}) => {
  const {
    chats,
    selectedChat,
    setSelectedChat,
    setVersions,
    setCurrentVersion,
    setIsLoading,
    setError,
  } = usePlayground();

  const handleChatClick = (chat: Chat) => {
    setSelectedChat(chat);
  };

  const handleNewChatClick = async () => {
    try {
      setIsLoading(false);

      // Clear everything to show empty playground screen
      setSelectedChat(null);
      setVersions([]);
      setCurrentVersion(null);
      setError(null);
    } catch (err) {
      console.error('New chat error:', err);
      setError(
        err instanceof Error ? err.message : 'Failed to create new chat',
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <aside className="w-72 bg-[#0a0e13] border-r border-[#1a2332] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#1a2332]">
        <button
          onClick={onClose}
          className="mb-4 p-1.5 hover:bg-[#1a2332] rounded transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        <button
          onClick={handleNewChatClick}
          className="flex items-center gap-3 w-full p-2.5 hover:bg-[#1a2332] rounded-lg transition-colors text-sm"
        >
          <MessageSquarePlus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        {/* <button className="flex items-center gap-3 w-full p-2.5 hover:bg-[#1a2332] rounded-lg transition-colors text-sm mt-1">
          <Search className="w-4 h-4" />
          <span>Search Chat</span>
        </button> */}
      </div>

      {/* Chats List */}
      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="text-sm font-semibold mb-3 text-white">
          Your Playgrounds
        </h2>

        {chats.length === 0 ? (
          <p className="text-sm text-gray-500">No chats yet</p>
        ) : (
          <ul className="space-y-1">
            {chats.map((chat) => (
              <li key={chat.id}>
                <button
                  onClick={() => handleChatClick(chat)}
                  className={`w-full text-left p-2.5 text-sm rounded-lg transition-colors ${
                    selectedChat?.id === chat.id
                      ? 'bg-teal-700 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-[#1a2332]'
                  }`}
                >
                  {chat.title}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
};
