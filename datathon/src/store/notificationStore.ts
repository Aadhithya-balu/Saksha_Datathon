import { create } from 'zustand';
import {
  getNotificationCount,
  getRecentNotifications,
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  dismissNotification,
} from '../services/api';
import type { NotificationRecord, NotificationCount, NotificationListResponse } from '../services/api';

interface NotificationState {
  // Data
  notifications: NotificationRecord[];
  recentNotifications: NotificationRecord[];
  counts: NotificationCount;
  total: number;
  page: number;
  pageSize: number;
  
  // UI State
  loading: boolean;
  loadingRecent: boolean;
  error: string | null;
  pollIntervalId: ReturnType<typeof setInterval> | null;

  // Actions
  fetchNotifications: (page?: number, pageSize?: number, unreadOnly?: boolean, notificationType?: string, severity?: string) => Promise<void>;
  fetchCounts: () => Promise<void>;
  fetchRecent: () => Promise<void>;
  markRead: (notificationId: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismiss: (notificationId: string) => Promise<void>;
  startPolling: (intervalMs?: number) => void;
  stopPolling: () => void;
  setPage: (page: number) => void;
  clearNotifications: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  recentNotifications: [],
  counts: { total: 0, unread: 0, critical: 0 },
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
  loadingRecent: false,
  error: null,
  pollIntervalId: null,

  fetchNotifications: async (page, pageSize, unreadOnly, notificationType, severity) => {
    set({ loading: true, error: null });
    try {
      const p = page ?? get().page;
      const ps = pageSize ?? get().pageSize;
      const response = await getNotifications(p, ps, unreadOnly ?? false, notificationType, severity);
      set({
        notifications: response.results,
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        loading: false,
      });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to load notifications', loading: false });
    }
  },

  fetchCounts: async () => {
    try {
      const counts = await getNotificationCount();
      set({ counts });
    } catch {
      // Silently fail for polling
    }
  },

  fetchRecent: async () => {
    set({ loadingRecent: true });
    try {
      const recent = await getRecentNotifications(5);
      set({ recentNotifications: recent, loadingRecent: false });
    } catch {
      set({ loadingRecent: false });
    }
  },

  markRead: async (notificationId) => {
    try {
      await markNotificationRead(notificationId);
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        ),
        recentNotifications: state.recentNotifications.map((n) =>
          n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        ),
      }));
      await get().fetchCounts();
    } catch (err: any) {
      set({ error: err?.message || 'Failed to mark notification as read' });
    }
  },

  markAllRead: async () => {
    try {
      await markAllNotificationsRead();
      const now = new Date().toISOString();
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true, read_at: now })),
        recentNotifications: state.recentNotifications.map((n) => ({ ...n, is_read: true, read_at: now })),
        counts: { ...state.counts, unread: 0 },
      }));
    } catch (err: any) {
      set({ error: err?.message || 'Failed to mark all as read' });
    }
  },

  dismiss: async (notificationId) => {
    try {
      await dismissNotification(notificationId);
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== notificationId),
        recentNotifications: state.recentNotifications.filter((n) => n.id !== notificationId),
      }));
      await get().fetchCounts();
    } catch (err: any) {
      set({ error: err?.message || 'Failed to dismiss notification' });
    }
  },

  startPolling: (intervalMs = 15000) => {
    const existing = get().pollIntervalId;
    if (existing) clearInterval(existing);

    const id = setInterval(async () => {
      await get().fetchCounts();
      await get().fetchRecent();
    }, intervalMs);

    set({ pollIntervalId: id });
  },

  stopPolling: () => {
    const id = get().pollIntervalId;
    if (id) {
      clearInterval(id);
      set({ pollIntervalId: null });
    }
  },

  setPage: (page) => {
    set({ page });
    get().fetchNotifications(page);
  },

  clearNotifications: () => {
    get().stopPolling();
    set({
      notifications: [],
      recentNotifications: [],
      counts: { total: 0, unread: 0, critical: 0 },
      error: null,
    });
  },
}));

