import React from 'react';
import type { GangNetworkSummary, GangHierarchyMember } from '../../services/api';
import { Users, Crosshair, MapPin, ArrowRight, UserCheck } from 'lucide-react';
import type { GraphNode } from './CriminalGraph3D';

interface GangNetworkViewProps {
  gangs: GangNetworkSummary[];
  selectedGang: GangNetworkSummary | null;
  onSelectGang: (gang: GangNetworkSummary) => void;
  onSelectMemberIn3D?: (node: GraphNode) => void;
}

export const GangNetworkView: React.FC<GangNetworkViewProps> = ({
  gangs,
  selectedGang,
  onSelectGang,
  onSelectMemberIn3D,
}) => {
  const activeGang = selectedGang || gangs[0];

  return (
    <div className="h-full flex flex-col gap-4 p-4 bg-[var(--bg-surface)] border border-[var(--border-secondary)] rounded-card font-mono overflow-y-auto">
      {/* Header */}
      <div className="border-b border-[var(--border-secondary)] pb-3">
        <h3 className="text-md font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
          <Users className="w-5 h-5 text-amber-400 animate-pulse" />
          Organized Crime & Gang Syndicate Network
        </h3>
        <p className="text-[10px] text-[var(--text-muted)] mt-1">
          HIERARCHICAL COMMAND TREES, SYNDICATE MEMBERSHIP, AND INTERSTATE OPERATIONAL RACKETS
        </p>
      </div>

      {/* Main Grid: Left Side Gang List, Right Side Hierarchy Tree */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1">
        {/* Gang Syndicate Cards List (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-2.5">
          <span className="text-[10px] text-[var(--text-muted)] uppercase font-bold tracking-wider">Identified Syndicates ({gangs.length})</span>
          {gangs.map((g) => {
            const isSelected = activeGang?.gang_id === g.gang_id;
            return (
              <div
                key={g.gang_id}
                onClick={() => onSelectGang(g)}
                className={`p-3.5 rounded-card border transition-all cursor-pointer flex flex-col gap-2 ${
                  isSelected
                    ? 'bg-[var(--bg-elevated)] border-[var(--accent-blue)] shadow-[0_0_15px_rgba(30,111,217,0.3)]'
                    : 'bg-[var(--bg-primary)] hover:bg-[var(--bg-tertiary)] border-[var(--border-primary)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[var(--text-primary)] uppercase">{g.name}</span>
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${
                      g.risk_level === 'CRITICAL'
                        ? 'bg-rose-950/60 text-rose-400 border border-rose-500/40'
                        : 'bg-amber-950/60 text-amber-400 border border-amber-500/40'
                    }`}
                  >
                    {g.risk_level}
                  </span>
                </div>

                <div className="text-[10px] text-[var(--text-muted)] space-y-1">
                  <div className="flex items-center gap-1.5 text-amber-300">
                    <Crosshair className="w-3 h-3" />
                    <span>Boss: {g.leader_name}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
                    <MapPin className="w-3 h-3 text-[var(--accent-blue)]" />
                    <span>{g.territory}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[9.5px] text-[var(--text-muted)] pt-2 border-t border-[var(--border-primary)]">
                  <span>{g.active_members} Active Operatives</span>
                  <ArrowRight className={`w-3.5 h-3.5 ${isSelected ? 'text-[var(--accent-blue)]' : 'text-[var(--text-primary)]/20'}`} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Gang Hierarchy Details (8 cols) */}
        {activeGang && (
          <div className="lg:col-span-8 bg-[var(--bg-primary)] p-4 rounded-card border border-[var(--border-secondary)] flex flex-col gap-4">
            {/* Gang Summary Header */}
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 p-3 bg-[var(--bg-tertiary)] rounded-card border border-[var(--border-primary)]">
              <div>
                <h4 className="text-sm font-bold text-[var(--text-primary)] uppercase">{activeGang.name}</h4>
                <p className="text-[10px] text-amber-400 font-bold uppercase mt-0.5">Primary Racket: {activeGang.primary_racket}</p>
              </div>
              <div className="text-[10px] text-right font-mono text-[var(--text-muted)]">
                <div>Territory: {activeGang.territory}</div>
                <div>Boss: <span className="text-[var(--text-primary)] font-bold">{activeGang.leader_name}</span></div>
              </div>
            </div>

            {/* Hierarchy Tree */}
            <div className="space-y-3">
              <span className="text-[11px] text-[var(--text-muted)] uppercase font-bold tracking-wider flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-[var(--accent-blue)]" />
                Command Hierarchy & Key Operatives
              </span>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {activeGang.members.map((member: GangHierarchyMember) => (
                  <div
                    key={member.id}
                    onClick={() =>
                      onSelectMemberIn3D?.({
                        id: member.id,
                        name: member.name,
                        category: member.rank_level === 1 ? 'suspect' : 'offender',
                        riskScore: member.riskScore,
                        details: member.role,
                        casesCount: member.casesCount,
                      })
                    }
                    className="p-3 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-elevated)] border border-[var(--border-secondary)] rounded-card transition-colors cursor-pointer flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40 text-[10px] font-bold flex items-center justify-center">
                          L{member.rank_level}
                        </span>
                        <span className="text-xs font-bold text-[var(--text-primary)] uppercase">{member.name}</span>
                      </div>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          member.status === 'at_large' ? 'bg-rose-950/60 text-rose-400' : 'bg-[var(--bg-elevated)] text-[var(--text-muted)]'
                        }`}
                      >
                        {member.status}
                      </span>
                    </div>

                    <div className="text-[10px] text-[var(--text-muted)] flex items-center justify-between pt-1 border-t border-[var(--border-primary)]">
                      <span>Role: <strong className="text-[var(--text-primary)]">{member.role}</strong></span>
                      <span className="text-amber-400 font-bold">Risk {member.riskScore}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Inter-member relationships */}
            {activeGang.relationships && activeGang.relationships.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[var(--border-primary)]">
                <span className="text-[10px] text-[var(--text-muted)] uppercase font-bold">Known Tactical Linkages:</span>
                <div className="flex flex-wrap gap-2 text-[10px]">
                  {activeGang.relationships.map((rel, idx) => (
                    <div key={`rel-${idx}`} className="px-2.5 py-1 bg-[var(--bg-tertiary)]/10 border border-[var(--border-secondary)] rounded text-[var(--text-muted)]">
                      <strong className="text-[var(--text-primary)]">{rel.source}</strong> ➔ <strong className="text-[var(--text-primary)]">{rel.target}</strong>: {rel.relationship}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GangNetworkView;
