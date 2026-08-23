import { useAuditStore } from '../store/auditStore';
import type { AuditLogEntry } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';

export const useAuditLog = () => {
  const addLog = useAuditStore((state) => state.addLog);
  const user = useAuthStore((state) => state.user);

  const logAction = (actionType: AuditLogEntry['actionType'], details: string) => {
    if (user) {
      addLog(user.name, user.badgeId, actionType, details);
    } else {
      addLog('Anonymous User', 'UNKNOWN', actionType, details);
    }
  };

  const logPageView = (pageName: string) => {
    logAction('PAGE_VIEW', `Navigated to ${pageName}`);
  };

  const logSearch = (query: string, category: string) => {
    logAction('SEARCH', `Searched for "${query}" in ${category}`);
  };

  const logExport = (fileName: string, format: string) => {
    logAction('EXPORT', `Exported ${fileName} as ${format.toUpperCase()}`);
  };

  return {
    logAction,
    logPageView,
    logSearch,
    logExport
  };
};
