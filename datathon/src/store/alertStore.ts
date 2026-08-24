import { create } from 'zustand';

export interface CrimeAlert {
  id: string;
  firNumber: string;
  caseUuid?: string;
  caseNumber?: string;
  district: string;
  station: string;
  crimeType: string;
  offenceDetails: string;
  anomalyScore: number; // 0-100%
  deviationPercent: number; // vs normal historical baseline
  severity: 'HIGH' | 'WATCH' | 'INFO';
  timestamp: string;
  status: 'PENDING' | 'REVIEWED' | 'ESCALATED';
  featureBreakdown: Record<string, number>; // features explaining anomaly score
  assignedOfficer?: string;
}

interface AlertState {
  alerts: CrimeAlert[];
  addAlert: (alert: Omit<CrimeAlert, 'id' | 'timestamp' | 'status'>) => void;
  reviewAlert: (id: string, reviewer: string) => void;
  escalateAlert: (id: string, reviewer: string) => void;
}

const INITIAL_ALERTS: CrimeAlert[] = [
  {
    id: 'alt-101',
    firNumber: 'FIR-045/BNG/2026',
    district: 'Bengaluru Urban',
    station: 'Indiranagar Police Station',
    crimeType: 'Cyber Crime & Online Fraud',
    offenceDetails: 'Massive volume surge in micro-lending app extortion campaigns using forged biometric face IDs.',
    anomalyScore: 94,
    deviationPercent: 320,
    severity: 'HIGH',
    timestamp: '2026-07-06T09:12:00Z',
    status: 'PENDING',
    featureBreakdown: { 'Frequency Spike': 85, 'IP Address Anomaly': 72, 'Victim Correlation': 90, 'Transaction Value': 66 },
  },
  {
    id: 'alt-102',
    firNumber: 'FIR-789/MYS/2026',
    district: 'Mysuru',
    station: 'Devaraja Police Station',
    crimeType: 'Theft & Burglaries',
    offenceDetails: 'Sequential residential break-ins matching historical MO of "Kodaikanal Ramu" gang, active after 2 years of dormancy.',
    anomalyScore: 87,
    deviationPercent: 180,
    severity: 'HIGH',
    timestamp: '2026-07-06T08:45:00Z',
    status: 'PENDING',
    featureBreakdown: { 'Modus Operandi Match': 98, 'Geographic Spacing': 78, 'Time Clustering': 82 },
  },
  {
    id: 'alt-103',
    firNumber: 'FIR-122/KLB/2026',
    district: 'Kalaburagi',
    station: 'Chowk Police Station',
    crimeType: 'Property Disputes',
    offenceDetails: 'Aggressive physical confrontation during land surveying involving known offender syndicate.',
    anomalyScore: 78,
    deviationPercent: 95,
    severity: 'WATCH',
    timestamp: '2026-07-06T07:30:00Z',
    status: 'REVIEWED',
    featureBreakdown: { 'Prior Offender Density': 80, 'Weapons Used Probability': 70, 'Political Sensitivity': 60 },
    assignedOfficer: 'Inspector R. Kumar'
  },
  {
    id: 'alt-104',
    firNumber: 'FIR-331/MNG/2026',
    district: 'Mangaluru',
    station: 'Pandeshwar Station',
    crimeType: 'Narcotics Smuggling Services',
    offenceDetails: 'Seizure of synthetic MDMA crystals at cargo terminal. Distribution nodes suggest darknet courier routing.',
    anomalyScore: 91,
    deviationPercent: 240,
    severity: 'HIGH',
    timestamp: '2026-07-06T06:15:00Z',
    status: 'PENDING',
    featureBreakdown: { 'Customs Anomaly': 93, 'Courier Identity Match': 84, 'Value Outlier': 88 },
  },
  {
    id: 'alt-105',
    firNumber: 'FIR-204/BLG/2026',
    district: 'Belagavi',
    station: 'Khade Bazar Station',
    crimeType: 'Smuggling & Excise Violations',
    offenceDetails: 'Interception of night cargo transport with forged inter-state transit clearance slips.',
    anomalyScore: 71,
    deviationPercent: 65,
    severity: 'WATCH',
    timestamp: '2026-07-06T05:00:00Z',
    status: 'PENDING',
    featureBreakdown: { 'Route Deviation': 75, 'Fake License Flag': 68, 'Cargo Manifest Discrepancy': 70 }
  }
];

export const useAlertStore = create<AlertState>((set) => ({
  alerts: INITIAL_ALERTS,
  
  addAlert: (alert) => set((state) => {
    const newAlert: CrimeAlert = {
      ...alert,
      id: `alt-${Math.floor(Math.random() * 1000) + 200}`,
      timestamp: new Date().toISOString(),
      status: 'PENDING'
    };
    return { alerts: [newAlert, ...state.alerts] };
  }),

  reviewAlert: (id, reviewer) => set((state) => ({
    alerts: state.alerts.map((a) => 
      a.id === id ? { ...a, status: 'REVIEWED', assignedOfficer: reviewer } : a
    )
  })),

  escalateAlert: (id, reviewer) => set((state) => ({
    alerts: state.alerts.map((a) => 
      a.id === id ? { ...a, status: 'ESCALATED', severity: 'HIGH', assignedOfficer: reviewer } : a
    )
  }))
}));
