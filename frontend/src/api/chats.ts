// src/api/chats.ts
import { apiCall } from './config';

// Raw shape from backend (Mongo/FastAPI)
export interface ChatResponse {
  id?: string;          // if backend already returns id
  _id?: string;         // if backend returns raw Mongo _id
  title: string;
  createdAt: string;
  updatedAt: string;
  currentVersionId: string | null;
  messageCount: number;
  isActive: boolean;
}

// What the rest of the frontend will use
export type Chat = ChatResponse & { id: string };

export interface CreateChatPayload {
  title: string;
}

// Normalize backend shape → frontend Chat
function normalizeChat(raw: ChatResponse): Chat {
  const id = raw.id ?? raw._id;
  if (!id) {
    throw new Error('Chat response missing id/_id');
  }

  // Strip _id if present
  const { _id, ...rest } = raw as any;
  return { ...rest, id };
}

export async function getAllChats(): Promise<Chat[]> {
  // Backend route: GET /api/chats/
  const rawChats = await apiCall<ChatResponse[]>('/chats/');
  return rawChats.map(normalizeChat);
}

export async function createChat(payload: CreateChatPayload): Promise<Chat> {
  // Backend route: POST /api/chats/
  const raw = await apiCall<ChatResponse>('/chats/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  return normalizeChat(raw);
}
