import { create } from 'zustand';

interface AppState {
  // Theme
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;

  // Sidebar
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;

  // Command Palette
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;

  // Mobile
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;

  // Navigation
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Breadcrumbs
  breadcrumbs: Array<{ label: string; tab?: string }>;
  setBreadcrumbs: (crumbs: Array<{ label: string; tab?: string }>) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Theme
  theme: (localStorage.getItem('saksha_theme') as 'dark' | 'light') || 'dark',
  setTheme: (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('saksha_theme', theme);
    set({ theme });
  },
  toggleTheme: () => {
    const newTheme = get().theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('saksha_theme', newTheme);
    set({ theme: newTheme });
  },

  // Sidebar
  sidebarCollapsed: localStorage.getItem('saksha_sidebar_collapsed') === 'true',
  setSidebarCollapsed: (collapsed) => {
    localStorage.setItem('saksha_sidebar_collapsed', String(collapsed));
    set({ sidebarCollapsed: collapsed });
  },
  toggleSidebar: () => {
    const newVal = !get().sidebarCollapsed;
    localStorage.setItem('saksha_sidebar_collapsed', String(newVal));
    set({ sidebarCollapsed: newVal });
  },

  // Command Palette
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  toggleCommandPalette: () => set({ commandPaletteOpen: !get().commandPaletteOpen }),

  // Mobile
  mobileMenuOpen: false,
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),

  // Navigation
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),

  // Breadcrumbs
  breadcrumbs: [],
  setBreadcrumbs: (crumbs) => set({ breadcrumbs: crumbs }),
}));
