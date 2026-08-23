import { create } from 'zustand';

export type AuditActionType =
  | 'PAGE_VIEW'
  | 'SEARCH'
  | 'EXPORT'
  | 'AUTH'
  | 'ESCALATION'
  | 'REVIEW'
  | 'CREATE'
  | 'UPDATE'
  | 'DELETE'
  | 'UPLOAD'
  | 'DOWNLOAD';

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  officerName: string;
  badgeId: string;
  actionType: AuditActionType;
  details: string;
  ipAddress: string;
}

interface AuditStore {
  logs: AuditLogEntry[];
  addLog: (officerName: string, badgeId: string, actionType: AuditLogEntry['actionType'], details: string) => void;
  clearLogs: () => void;
}

const INITIAL_LOGS: AuditLogEntry[] = [
  {
    id: 'log-001',
    timestamp: '2026-07-06T09:00:22Z',
    officerName: 'DCP Rajesh Kumar',
    badgeId: 'SCRB-7740',
    actionType: 'AUTH',
    details: 'Successful biometric authentication via Facial ID',
    ipAddress: '10.144.12.89',
  },
  {
    id: 'log-002',
    timestamp: '2026-07-06T09:01:05Z',
    officerName: 'DCP Rajesh Kumar',
    badgeId: 'SCRB-7740',
    actionType: 'PAGE_VIEW',
    details: 'Accessed Overview Dashboard',
    ipAddress: '10.144.12.89',
  },
  {
    id: 'log-003',
    timestamp: '2026-07-06T09:02:15Z',
    officerName: 'DCP Rajesh Kumar',
    badgeId: 'SCRB-7740',
    actionType: 'SEARCH',
    details: 'Queried offender network database for term "Ramu"',
    ipAddress: '10.144.12.89',
  },
  {
    id: 'log-004',
    timestamp: '2026-07-06T09:03:54Z',
    officerName: 'DCP Rajesh Kumar',
    badgeId: 'SCRB-7740',
    actionType: 'EXPORT',
    details: 'Exported crime density heatmap as CONFIDENTIAL PDF for Bengaluru Urban',
    ipAddress: '10.144.12.89',
  }
];

export const useAuditStore = create<AuditStore>((set) => ({
  logs: INITIAL_LOGS,
  
  addLog: (officerName, badgeId, actionType, details) => set((state) => {
    const newLog: AuditLogEntry = {
      id: `log-${Math.floor(Math.random() * 100000)}`,
      timestamp: new Date().toISOString(),
      officerName,
      badgeId,
      actionType,
      details,
      ipAddress: '10.0.' + (Math.floor(Math.random() * 254) + 1) + '.' + (Math.floor(Math.random() * 254) + 1)
    };
    return { logs: [newLog, ...state.logs] };
  }),

  clearLogs: () => set({ logs: [] })
}));
export default useAuditStore;
