import { create } from 'zustand';
import { connectRealtime, type RealtimeEvent, type RealtimeStatus } from '../services/realtime';

export interface LiveCase {
  id?: string;
  case_number: string;
  crime_type: string;
  location: string;
  time: string | null;
  status: string;
  priority: string;
}

type CaseListener = (eventCase: LiveCase) => void;

interface RealtimeState {
  status: RealtimeStatus;
  liveCases: LiveCase[];
  connect: () => void;
  disconnect: () => void;
  onCaseCreated: (listener: CaseListener) => () => void;
  clearLiveCases: () => void;
}

const MAX_LIVE_CASES = 25;

let disconnectStream: (() => void) | null = null;
let consumerCount = 0;
const caseListeners = new Set<CaseListener>();

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  status: 'disconnected',
  liveCases: [],

  connect: () => {
    consumerCount += 1;
    if (disconnectStream) return;

    const handleEvent = (event: RealtimeEvent) => {
      if (event.type !== 'case_created') return;
      const liveCase: LiveCase = event.data;
      set((state) => ({
        liveCases: [
          liveCase,
          ...state.liveCases.filter((c) => c.case_number !== liveCase.case_number),
        ].slice(0, MAX_LIVE_CASES),
      }));
      caseListeners.forEach((listener) => listener(liveCase));
    };

    disconnectStream = connectRealtime({
      onEvent: handleEvent,
      onStatus: (status) => set({ status }),
    });
  },

  disconnect: () => {
    consumerCount = Math.max(consumerCount - 1, 0);
    if (consumerCount === 0 && disconnectStream) {
      disconnectStream();
      disconnectStream = null;
      set({ status: 'disconnected' });
    }
  },

  onCaseCreated: (listener) => {
    caseListeners.add(listener);
    return () => caseListeners.delete(listener);
  },

  clearLiveCases: () => {
    if (get().liveCases.length > 0) set({ liveCases: [] });
  },
}));
