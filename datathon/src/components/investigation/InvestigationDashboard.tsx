import React from 'react';
import { Calendar, Clock, MapPin, User, Shield, AlertTriangle } from 'lucide-react';
import type { InvestigationCase } from '../../services/api';

interface Props {
  data: InvestigationCase;
}

const InvestigationDashboard: React.FC<Props> = ({ data }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'closed': return 'text-emerald-400 bg-emerald-950/30 border-emerald-900/40';
      case 'charge sheet filed': return 'text-blue-400 bg-blue-950/30 border-blue-900/40';
      case 'open': return 'text-amber-400 bg-amber-950/30 border-amber-900/40';
      default: return 'text-cyan-400 bg-cyan-950/30 border-cyan-900/40';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'text-red-400 bg-red-950/30 border-red-900/40';
      case 'high': return 'text-orange-400 bg-orange-950/30 border-orange-900/40';
      case 'medium': return 'text-yellow-400 bg-yellow-950/30 border-yellow-900/40';
      default: return 'text-green-400 bg-green-950/30 border-green-900/40';
    }
  };

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card shadow-glow-blue/5">
      {/* Case Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="text-[10px] text-[#0E9E78] font-bold tracking-[0.15em] uppercase">
            SAKSHA INVESTIGATION DASHBOARD
          </span>
          <h1 className="text-xl md:text-2xl font-bold text-white uppercase tracking-wider mt-1">
            {data.case_number}
          </h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2.5 py-1 text-[9px] rounded font-bold uppercase border ${getStatusColor(data.status)}`}>
            {data.status.replace(/_/g, ' ')}
          </span>
          <span className={`px-2.5 py-1 text-[9px] rounded font-bold uppercase border ${getPriorityColor(data.priority)}`}>
            {data.priority} PRIORITY
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-[#A8B4CC] leading-relaxed border-t border-border-color/60 mt-4 pt-4">
        {data.description || 'NO DESCRIPTION PROVIDED FOR THIS CASE.'}
      </p>

      {/* Meta Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border-color/30 text-[10px] text-[#6A7A96] uppercase">
        <div className="flex items-center gap-2">
          <Calendar className="w-3.5 h-3.5 text-[#1E6FD9]" />
          <span>REPORTED: {new Date(data.reported_at).toLocaleDateString()}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-[#0E9E78]" />
          <span>OCCURRED: {new Date(data.occurred_at).toLocaleDateString()}</span>
        </div>
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-[#6C43CC]" />
          <span>PROGRESS: {data.progress}%</span>
        </div>
        <div className="flex items-center gap-2">
          {data.assigned_officer ? (
            <>
              <User className="w-3.5 h-3.5 text-[#1E6FD9]" />
              <span className="truncate">{data.assigned_officer.full_name}</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span>UNASSIGNED</span>
            </>
          )}
        </div>
      </div>

      {/* MO Tags */}
      {data.mo_tags && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-color/20">
          <MapPin className="w-3 h-3 text-[#C94A2A]" />
          <div className="flex gap-1.5 flex-wrap">
            {data.mo_tags.split(',').map((tag, i) => (
              <span key={i} className="px-1.5 py-0.5 bg-slate-950/60 border border-slate-900 rounded text-[8px] text-[#A8B4CC] uppercase font-mono">
                {tag.trim()}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationDashboard;

