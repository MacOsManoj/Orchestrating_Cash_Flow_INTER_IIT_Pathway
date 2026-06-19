import React, { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { ChatSidebar } from '../components/ChatSidebar';
import { CanvasArea } from '../components/CanvasArea';
import { ConversationSidebar } from '../components/ConversationSidebar';
import { usePlayground } from '../context/PlaygroundContext';

export const PlaygroundActive: React.FC = () => {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  
  const { selectedChat, error } = usePlayground();

  return (
    <div className="flex h-screen bg-[#0a0e14] text-white relative">
      {/* Error display */}
      {error && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-900/90 border border-red-700 px-4 py-2 rounded-lg z-50">
          <p className="text-sm text-white">{error}</p>
        </div>
      )}

      {/* Left Sidebar - Chat List */}
      <ChatSidebar 
        isOpen={leftSidebarOpen} 
        onClose={() => setLeftSidebarOpen(false)} 
      />

      {/* Canvas Area */}
      <CanvasArea />

      {/* Right Sidebar - Conversation (messages + versions) */}
      {selectedChat && (
        <ConversationSidebar 
          isOpen={rightSidebarOpen} 
          onClose={() => setRightSidebarOpen(false)} 
        />
      )}

      {/* Expand button for left sidebar */}
      {!leftSidebarOpen && (
        <button
          onClick={() => setLeftSidebarOpen(true)}
          className="absolute top-4 left-4 p-2 bg-[#1a2332] hover:bg-[#2a3a4a] rounded-lg transition-colors z-20"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      )}

      {/* Expand button for right sidebar */}
      {!rightSidebarOpen && selectedChat && (
        <button
          onClick={() => setRightSidebarOpen(true)}
          className="absolute top-4 right-4 p-2 bg-[#1a2332] hover:bg-[#2a3a4a] rounded-lg transition-colors z-20"
        >
          <ChevronRight className="w-5 h-5 transform rotate-180" />
        </button>
      )}
    </div>
  );
};