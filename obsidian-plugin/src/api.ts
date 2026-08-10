import { requestUrl } from "obsidian";
import { normalizeServerUrl, type PluginSettings } from "./utils";

export interface TextItem {
  id: string;
  message_id: number;
  content: string;
  short: boolean;
  created_at: string;
  images: string[];
}

export interface YoutubeItem {
  id: string;
  url: string;
  title: string;
  duration: number | null;
  created_at: string;
}

function apiBase(settings: PluginSettings): string {
  return normalizeServerUrl(settings.serverUrl);
}

function authHeaders(settings: PluginSettings): Record<string, string> {
  return {
    Authorization: `Bearer ${settings.bearerToken}`,
  };
}

async function apiJson<T>(
  settings: PluginSettings,
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${apiBase(settings)}${path}`;
  try {
    const res = await requestUrl({
      url,
      method,
      headers: {
        ...authHeaders(settings),
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      throw: false,
    });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`HTTP ${res.status} ${method} ${path}: ${res.text}`);
    }
    if (!res.text) {
      return {} as T;
    }
    return JSON.parse(res.text) as T;
  } catch (err) {
    console.error(`[tg-obsidian-sync] ${method} ${path} failed`, err);
    throw err;
  }
}

export async function fetchTexts(settings: PluginSettings): Promise<TextItem[]> {
  return apiJson<TextItem[]>(settings, "GET", "/api/v1/texts?limit=200&offset=0");
}

export async function fetchYoutube(settings: PluginSettings): Promise<YoutubeItem[]> {
  return apiJson<YoutubeItem[]>(settings, "GET", "/api/v1/youtube");
}

export async function ackTexts(
  settings: PluginSettings,
  messageIds: number[],
): Promise<void> {
  if (!messageIds.length) return;
  await apiJson(settings, "POST", "/api/v1/texts/ack", { message_ids: messageIds });
}

export async function ackYoutube(
  settings: PluginSettings,
  ids: string[],
): Promise<void> {
  if (!ids.length) return;
  await apiJson(settings, "POST", "/api/v1/youtube/ack", { ids });
}

export async function cleanupServer(settings: PluginSettings): Promise<void> {
  await apiJson(settings, "DELETE", "/api/v1/cleanup");
}

export async function downloadMedia(
  settings: PluginSettings,
  fileName: string,
): Promise<ArrayBuffer> {
  const url = `${apiBase(settings)}/api/v1/media/${encodeURIComponent(fileName)}`;
  try {
    const res = await requestUrl({
      url,
      method: "GET",
      headers: authHeaders(settings),
      throw: false,
    });
    if (res.status < 200 || res.status >= 300) {
      throw new Error(`HTTP ${res.status} downloading ${fileName}`);
    }
    return res.arrayBuffer;
  } catch (err) {
    console.error(`[tg-obsidian-sync] media download failed: ${fileName}`, err);
    throw err;
  }
}
