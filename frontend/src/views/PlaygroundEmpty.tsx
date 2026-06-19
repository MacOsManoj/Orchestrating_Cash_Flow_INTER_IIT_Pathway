import React, { useState } from 'react';
import { PromptInput } from '../components/PromptInput';
import { ChatSidebar } from '../components/ChatSidebar';
import { ChevronRight } from 'lucide-react';

export const PlaygroundEmpty: React.FC = () => {
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen bg-[#0a0e14] text-white relative">
      {/* Left Sidebar - Chat List */}
      <ChatSidebar 
        isOpen={leftSidebarOpen} 
        onClose={() => setLeftSidebarOpen(false)}
      />

      {/* Expand button for left sidebar */}
      {!leftSidebarOpen && (
        <button
          onClick={() => setLeftSidebarOpen(true)}
          className="absolute top-4 left-4 p-2 bg-[#1a2332] hover:bg-[#2a3a4a] rounded-lg transition-colors z-20"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      )}

      {/* Center content */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[#0f1419]">
        <div className="w-full max-w-3xl flex flex-col items-center">
          {/* Header Text */}
          <div className="text-center mb-32">
            <h1 className="text-5xl font-bold mb-3 text-white">Ready to begin?</h1>
            <p className="text-gray-400 text-lg">Explore with Playground</p>
          </div>

          {/* Prompt Input */}
          <PromptInput />
        </div>
      </div>
    </div>
  );
};