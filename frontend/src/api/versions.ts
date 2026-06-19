import { apiCall } from "./config";

// Raw version as returned by backend
export interface VersionResponse {
  id?: string;     // if backend already aliases _id → id via Pydantic
  _id?: string;    // if raw Mongo shape leaks through
  chatId: string;
  versionNumber: number;
  prompt: string;
  message?: string;          // 🆕 agent message
  components: any[];         // 🧹 now a list from backend
  createdAt: string;
}

// What the app actually uses
export type Version = VersionResponse & { id: string };

// Normalize backend object → frontend Version
function normalizeVersion(raw: VersionResponse): Version {
  const id = raw.id ?? raw._id;
  if (!id) {
    throw new Error("Version response missing id/_id");
  }

  const { _id, ...rest } = raw as any;
  return { ...rest, id };
}

// GET /chats/:chatId/versions
export async function getChatVersions(chatId: string): Promise<Version[]> {
  const raw = await apiCall<VersionResponse[]>(`/chats/${chatId}/versions`);
  return raw.map(normalizeVersion);
}

// POST /chats/:chatId/versions
interface CreateVersionPayload {
  prompt: string;
  versionNumber: number;
}

export async function createVersion(
  chatId: string,
  payload: CreateVersionPayload,
): Promise<Version> {
  const raw = await apiCall<VersionResponse>(`/chats/${chatId}/versions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeVersion(raw);
}

// Optionally: GET latest version
export async function getLatestVersion(chatId: string): Promise<Version> {
  const raw = await apiCall<VersionResponse>(
    `/chats/${chatId}/versions/latest`,
  );
  return normalizeVersion(raw);
}
