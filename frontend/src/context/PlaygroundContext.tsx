// src/context/PlaygroundContext.tsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from 'react';

import { getAllChats, type Chat } from '../api/chats';
import { getChatVersions, type Version } from '../api/versions';
import { getChatMessages, type Message } from '../api/messages';

interface PlaygroundContextType {
  // Chat state
  chats: Chat[];
  setChats: React.Dispatch<React.SetStateAction<Chat[]>>;
  selectedChat: Chat | null;
  setSelectedChat: React.Dispatch<React.SetStateAction<Chat | null>>;

  // Version state
  versions: Version[];
  setVersions: React.Dispatch<React.SetStateAction<Version[]>>;
  currentVersion: Version | null;
  setCurrentVersion: React.Dispatch<React.SetStateAction<Version | null>>;

  // Message state
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;

  // UI state
  isLoading: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}

const PlaygroundContext = createContext<PlaygroundContextType | undefined>(
  undefined,
);

export const usePlayground = () => {
  const context = useContext(PlaygroundContext);
  if (!context) {
    throw new Error('usePlayground must be used within PlaygroundProvider');
  }
  return context;
};

interface PlaygroundProviderProps {
  children: ReactNode;
}

export const PlaygroundProvider: React.FC<PlaygroundProviderProps> = ({
  children,
}) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [currentVersion, setCurrentVersion] = useState<Version | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1) On mount, ONLY load the list of chats. Don't auto-select any.
  useEffect(() => {
    let cancelled = false;

    async function loadChats() {
      setIsLoading(true);
      try {
        const allChats = await getAllChats();
        if (!cancelled) {
          setChats(allChats);
        }
      } catch (err) {
        console.error('Failed to fetch chats', err);
        if (!cancelled) {
          setError('Failed to fetch chats');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadChats();
    return () => {
      cancelled = true;
    };
  }, []);

  // 2) When selectedChat changes, load versions + messages for that chat
  useEffect(() => {
    let cancelled = false;

    async function loadChatData() {
      if (!selectedChat) {
        setVersions([]);
        setMessages([]);
        setCurrentVersion(null);
        return;
      }

      const chatId = selectedChat.id ?? (selectedChat as any)._id ?? null;

      if (!chatId) {
        console.error(
          'Selected chat has no id/_id; cannot load data:',
          selectedChat,
        );
        return;
      }

      setIsLoading(true);
      try {
        const chatVersions = await getChatVersions(chatId);
        if (cancelled) return;

        setVersions(chatVersions);
        setCurrentVersion(chatVersions[0] ?? null);

        try {
          const chatMessages = await getChatMessages(chatId);
          if (!cancelled) {
            setMessages(chatMessages);
          }
        } catch (err) {
          console.warn(
            'Failed to load messages for chat; treating as empty:',
            err,
          );
          if (!cancelled) {
            setMessages([]);
          }
        }
      } catch (err) {
        console.error('Failed to load chat data', err);
        if (!cancelled) {
          setError('Failed to load chat data');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadChatData();
    return () => {
      cancelled = true;
    };
  }, [selectedChat]);

  return (
    <PlaygroundContext.Provider
      value={{
        chats,
        setChats,
        selectedChat,
        setSelectedChat,
        versions,
        setVersions,
        currentVersion,
        setCurrentVersion,
        messages,
        setMessages,
        isLoading,
        setIsLoading,
        error,
        setError,
      }}
    >
      {children}
    </PlaygroundContext.Provider>
  );
};
