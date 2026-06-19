// src/api/messages.ts
import { apiCall } from './config';

export type MessageRole = 'user' | 'assistant';

export interface Message {
  id: string;
  chatId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

/**
 * Get all messages for a chat.
 * Backend route: GET /api/chats/{chatId}/messages
 */
export async function getChatMessages(
  chatId: string,
): Promise<Message[]> {
  return apiCall<Message[]>(`/chats/${chatId}/messages`);
}
