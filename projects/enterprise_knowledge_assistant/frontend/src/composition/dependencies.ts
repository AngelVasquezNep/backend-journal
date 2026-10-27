/** Composition root supplies runtime and HTTP adapters to framework-free application ports. */
import { BrowserRuntime, BrowserAttachment } from '@/adapters/outbound/browser/runtime';
import { BrowserDownloads } from '@/adapters/outbound/browser/downloads';
import { KnowledgeHTTP } from '@/adapters/outbound/http/knowledge';
import { KnowledgeController } from '@/application/knowledge';
import { UsersHTTP } from '@/adapters/outbound/http/users';
import { createCompanyUser } from '@/application/create_user';
import { ChatHTTP } from '@/adapters/outbound/http/chat';
import { ChatController } from '@/application/chat';
import { HttpClient } from '@/adapters/outbound/http/client';
import { AuthHTTP } from '@/adapters/outbound/http/auth';
import { AuthController } from '@/application/auth';

/** Construct browser dependencies explicitly; no credentials or transcript are persisted. */
export function createDependencies() {
  const runtime = new BrowserRuntime();
  const http = new HttpClient(window.fetch.bind(window), window.location.origin);
  const accountCaches = new Set<() => void>();
  const auth = new AuthController(new AuthHTTP(http), () => { for (const clear of accountCaches) clear(); });
  http.onAuthenticationLost = () => { auth.clear(); };
  const knowledge = new KnowledgeController(new KnowledgeHTTP(http), runtime, new BrowserDownloads());
  accountCaches.add(() => { knowledge.clear(); });
  const users = new UsersHTTP(http);
  const chat = new ChatController(new ChatHTTP(http), runtime, runtime, new BrowserDownloads());
  accountCaches.add(() => { chat.clear(); });
  return { runtime, http, auth, knowledge, chat, accountCaches, wrapFile: (file: File) => new BrowserAttachment(file), createUser: (name: string, email: string, password: string) => createCompanyUser(users, name, email, password) };
}
