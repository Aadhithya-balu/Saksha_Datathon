import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAlertStore } from '../../store/alertStore';
import type { CrimeAlert } from '../../store/alertStore';
import { AlertCircle, Eye, ShieldAlert, CheckCircle, Navigation } from 'lucide-react';

interface AlertFeedProps {
  onAlertClick?: (alert: CrimeAlert) => void;
  limit?: number;
}

export const AlertFeed: React.FC<AlertFeedProps> = ({ onAlertClick, limit = 5 }) => {
  const alerts = useAlertStore((state) => state.alerts);
  const activeAlerts = alerts.slice(0, limit);

  return (
    <div className="flex flex-col gap-3">
      {/* Feed Header */}
      <div className="flex justify-between items-center select-none mb-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#C94A2A] animate-ping" />
          <h4 className="text-[11px] font-mono uppercase tracking-widest text-[#E8EDF5]">
            Critical Anomaly Feed
          </h4>
        </div>
        <span className="px-2 py-0.5 bg-[#C94A2A]/10 text-[#C94A2A] rounded-full text-[9px] font-bold font-mono border border-[#C94A2A]/20">
          {alerts.filter(a => a.status === 'PENDING').length} PENDING UNRESOLVED
        </span>
      </div>

      {/* Cards list */}
      <div className="flex flex-col gap-2.5 overflow-y-auto max-h-[460px] pr-1.5 custom-scrollbar">
        <AnimatePresence initial={false}>
          {activeAlerts.map((alert, index) => {
            const isHigh = alert.severity === 'HIGH';
            const isWatch = alert.severity === 'WATCH';
            
            // Pulsing border styles
            const borderClass = isHigh 
              ? 'border-l-[3.5px] border-l-[#C94A2A] pulse-border-red' 
              : isWatch 
              ? 'border-l-[3.5px] border-l-[#D4820A] pulse-border-amber' 
              : 'border-l-[3.5px] border-l-[#1E6FD9]';

            return (
              <motion.div
                key={alert.id}
                initial={{ x: 120, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -100, opacity: 0 }}
                transition={{ 
                  type: 'spring', 
                  stiffness: 140, 
                  damping: 15,
                  mass: 0.8,
                  delay: index * 0.05 
                }}
                onClick={() => onAlertClick?.(alert)}
                className={`p-3.5 bg-slate-950/40 border border-border-color hover:border-[#1E6FD9]/30 rounded-card cursor-pointer flex flex-col gap-2 text-left relative overflow-hidden transition-all duration-300 ${borderClass}`}
              >
                {/* Top card row */}
                <div className="flex justify-between items-start">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-[#E8EDF5] font-bold">
                      {alert.firNumber}
                    </span>
                    <span className="text-[8px] font-mono text-[#6A7A96] uppercase mt-0.5">
                      {alert.station} • {alert.district}
                    </span>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[8.5px] font-mono font-bold ${
                    isHigh 
                      ? 'bg-[#C94A2A]/10 text-[#C94A2A] border border-[#C94A2A]/20' 
                      : isWatch 
                      ? 'bg-[#D4820A]/10 text-[#D4820A] border border-[#D4820A]/20' 
                      : 'bg-[#1E6FD9]/10 text-[#1E6FD9] border border-[#1E6FD9]/20'
                  }`}>
                    {alert.severity} SCORE: {alert.anomalyScore}%
                  </span>
                </div>

                {/* Details Section */}
                <p className="text-[10.5px] text-[#A8B4CC] leading-relaxed line-clamp-2">
                  {alert.offenceDetails}
                </p>

                {/* Footer status markers */}
                <div className="flex justify-between items-center mt-1 border-t border-slate-900 pt-2 text-[9px] font-mono">
                  <div className="flex items-center gap-1.5">
                    {alert.status === 'PENDING' ? (
                      <span className="text-red-400 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 animate-pulse" />
                        UNRESOLVED
                      </span>
                    ) : alert.status === 'REVIEWED' ? (
                      <span className="text-[#0E9E78] flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        UNDER INVESTIGATION
                      </span>
                    ) : (
                      <span className="text-[#6C43CC] flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3" />
                        ESCALATED TO SP
                      </span>
                    )}
                  </div>
                  
                  <span className="text-[#6A7A96]">
                    {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} IST
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        
        {activeAlerts.length === 0 && (
          <div className="p-8 text-center text-xs font-mono text-[#6A7A96] uppercase select-none border border-dashed border-border-color/30 rounded-card">
            No Active Anomalies Detected
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertFeed;
