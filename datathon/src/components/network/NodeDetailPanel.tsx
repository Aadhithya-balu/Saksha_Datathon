import React from 'react';
import type { GraphNode, GraphLink } from './CriminalGraph3D';
import { User, ShieldAlert, Phone, MapPin, Briefcase, X, Database, FileText, Share2, Waypoints, Focus } from 'lucide-react';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';

interface NodeDetailPanelProps {
  node: GraphNode | null;
  links?: GraphLink[];
  nodes?: GraphNode[];
  onClose: () => void;
  onSelectNode?: (node: GraphNode) => void;
  onSelectLink?: (link: GraphLink) => void;
  /** Issue #230: investigative actions — set as path-finder endpoint or focus
   *  the graph around this entity. Optional so other views keep working. */
  onSetPathSource?: (node: GraphNode) => void;
  onSetPathTarget?: (node: GraphNode) => void;
  onFocusNode?: (node: GraphNode, hops: number) => void;
  onClearFocus?: () => void;
  isFocused?: boolean;
  focusHops?: number;
}

export const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ 
  node, 
  links = [], 
  nodes = [], 
  onClose,
  onSelectNode,
  onSelectLink,
  onSetPathSource,
  onSetPathTarget,
  onFocusNode,
  onClearFocus,
  isFocused = false,
  focusHops = 2,
}) => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  if (!node) return null;

  const isSuspect = node.category === 'suspect';
  const isOffender = node.category === 'offender';
  const isLocation = node.category === 'location';
  const isVictim = node.category === 'victim';

  const connectedLinks = links.filter((l) => {
    const sId = typeof l.source === 'object' ? l.source.id : l.source;
    const tId = typeof l.target === 'object' ? l.target.id : l.target;
    return sId === node.id || tId === node.id;
  });

  const connectedNodes = connectedLinks.map((link) => {
    const sId = typeof link.source === 'object' ? link.source.id : link.source;
    const tId = typeof link.target === 'object' ? link.target.id : link.target;
    const otherId = sId === node.id ? tId : sId;
    const otherNode = nodes.find((n) => n.id === otherId);
    return { link, otherNode, otherName: otherNode?.name || otherId };
  });

  const riskColor = node.riskScore >= 80 ? 'var(--accent-coral)' : node.riskScore >= 50 ? 'var(--accent-amber)' : 'var(--accent-teal)';

  return (
    <div className="h-full bg-secondary-bg border-l border-border-color flex flex-col select-none overflow-hidden">
      
      {/* Header */}
      <div className="p-4 pb-3 border-b border-border-color shrink-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-10 h-10 shrink-0 rounded-full flex items-center justify-center ${
              isSuspect ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 
              isOffender ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
              isLocation ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
              isVictim ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' :
              'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            }`}>
              {isLocation ? <MapPin className="w-5 h-5" /> : <User className="w-5 h-5" />}
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">{node.name}</h3>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5 capitalize">{node.category}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer shrink-0 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {node.isSeed && (
          <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--accent-purple)]/10 border border-[var(--accent-purple)]/20 text-[var(--accent-purple)] text-[10px]">
            <Database className="w-3 h-3" />
            Demo seed record
          </div>
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-sm">
        
        {/* Risk score */}
        {!isVictim && !isLocation && (
          <div className="flex items-center justify-between p-3 rounded-lg border" style={{ backgroundColor: `${riskColor}08`, borderColor: `${riskColor}25` }}>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Risk Score</p>
              <p className="text-xl font-bold mt-0.5" style={{ color: riskColor }}>{node.riskScore}%</p>
            </div>
            <ShieldAlert className="w-5 h-5 animate-pulse" style={{ color: riskColor }} />
          </div>
        )}

        {/* Location severity */}
        {isLocation && (
          <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/20">
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Location Severity</p>
            <p className="text-xl font-bold text-sky-400 mt-0.5">{node.riskScore}%</p>
          </div>
        )}

        {/* Details */}
        {node.details && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] mb-1.5">Details</p>
            <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-secondary)] p-3 rounded-lg border border-[var(--border-color)]">
              {node.details}
            </p>
          </div>
        )}

        {/* Quick info */}
        <div className="space-y-2">
          {node.phone && (
            <div className="flex items-center gap-2 text-[13px]">
              <Phone className="w-3.5 h-3.5 text-[var(--accent-blue)] shrink-0" />
              <span className="text-[var(--text-muted)]">Contact</span>
              <span className="ml-auto text-[var(--text-primary)]">{node.phone}</span>
            </div>
          )}
          {node.gangAffiliation && (
            <div className="flex items-center gap-2 text-[13px]">
              <ShieldAlert className="w-3.5 h-3.5 text-[var(--accent-coral)] shrink-0" />
              <span className="text-[var(--text-muted)]">Gang</span>
              <span className="ml-auto text-[var(--text-primary)]">{node.gangAffiliation}</span>
            </div>
          )}
          {node.status && (
            <div className="flex items-center gap-2 text-[13px]">
              <Briefcase className="w-3.5 h-3.5 text-[var(--accent-teal)] shrink-0" />
              <span className="text-[var(--text-muted)]">Status</span>
              <span className="ml-auto text-[var(--text-primary)] capitalize">{node.status.replace(/_/g, ' ')}</span>
            </div>
          )}
          {node.district && (
            <div className="flex items-center gap-2 text-[13px]">
              <MapPin className="w-3.5 h-3.5 text-[var(--accent-purple)] shrink-0" />
              <span className="text-[var(--text-muted)]">District</span>
              <span className="ml-auto text-[var(--text-primary)]">{node.district}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-[13px]">
            <Briefcase className="w-3.5 h-3.5 text-[var(--accent-amber)] shrink-0" />
            <span className="text-[var(--text-muted)]">Linked cases</span>
            <span className="ml-auto text-[var(--text-primary)]">{node.casesCount}</span>
          </div>
        </div>

        {/* Connected entities */}
        {connectedNodes.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
                Connections ({connectedNodes.length})
              </p>
              <span className="text-[9px] text-[var(--text-muted)]">Click person to navigate</span>
            </div>
            <div className="space-y-1.5">
              {connectedNodes.slice(0, 10).map(({ otherName, link, otherNode }, i) => (
                <div 
                  key={i} 
                  onClick={() => {
                    if (otherNode && onSelectNode) {
                      onSelectNode(otherNode);
                    } else if (onSelectLink) {
                      onSelectLink(link);
                    }
                  }}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-[var(--bg-secondary)] hover:bg-[var(--accent-blue)]/15 border border-[var(--border-color)] hover:border-[var(--accent-blue)]/40 text-[12px] cursor-pointer transition-all group"
                  title={`View ${otherName} details & network`}
                >
                  <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{
                    backgroundColor: link.verification_status === 'VERIFIED' ? 'var(--accent-teal)' : link.verification_status === 'POTENTIAL' ? 'var(--accent-amber)' : 'var(--text-muted)'
                  }} />
                  <span className="text-[var(--text-primary)] group-hover:text-[var(--accent-blue)] truncate font-medium">{otherName}</span>
                  <span 
                    onClick={(e) => {
                      if (onSelectLink) {
                        e.stopPropagation();
                        onSelectLink(link);
                      }
                    }}
                    className="ml-auto text-[10px] text-[var(--text-muted)] group-hover:text-[var(--text-secondary)] shrink-0 hover:underline"
                    title="Inspect relationship link"
                  >
                    {link.relationship}
                  </span>
                </div>
              ))}
              {connectedNodes.length > 10 && (
                <p className="text-[10px] text-[var(--text-muted)] text-center pt-1">+ {connectedNodes.length - 10} more</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border-color shrink-0 space-y-1.5">
        {/* Issue #230: investigative actions (only rendered when wired up) */}
        {(onSetPathSource || onSetPathTarget || onFocusNode || onClearFocus) && (
          <div className="space-y-1.5 pb-1">
            <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold">Investigation Actions</p>
            <div className="grid grid-cols-2 gap-1.5">
              {onSetPathSource && (
                <button
                  onClick={() => onSetPathSource(node)}
                  className="py-1.5 px-2 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] uppercase rounded-lg font-bold cursor-pointer flex items-center justify-center gap-1 transition-colors"
                  title="Use this entity as the starting point of a connection-path search"
                >
                  <Waypoints className="w-3 h-3" />
                  Set as Source
                </button>
              )}
              {onSetPathTarget && (
                <button
                  onClick={() => onSetPathTarget(node)}
                  className="py-1.5 px-2 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] uppercase rounded-lg font-bold cursor-pointer flex items-center justify-center gap-1 transition-colors"
                  title="Use this entity as the destination of a connection-path search"
                >
                  <Waypoints className="w-3 h-3" />
                  Set as Target
                </button>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              {onFocusNode && (
                <>
                  <button
                    onClick={() => onFocusNode(node, 1)}
                    className={`py-1 px-2 text-[9px] uppercase rounded-lg font-bold border cursor-pointer transition-colors ${
                      isFocused && focusHops === 1
                        ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] border-[var(--accent-blue)]'
                        : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/20 text-[var(--text-secondary)] border-[var(--border-color)]'
                    }`}
                  >
                    1 hop
                  </button>
                  <button
                    onClick={() => onFocusNode(node, 2)}
                    className={`py-1 px-2 text-[9px] uppercase rounded-lg font-bold border cursor-pointer transition-colors ${
                      isFocused && focusHops === 2
                        ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] border-[var(--accent-blue)]'
                        : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/20 text-[var(--text-secondary)] border-[var(--border-color)]'
                    }`}
                  >
                    2 hops
                  </button>
                  <button
                    onClick={() => onFocusNode(node, 3)}
                    className={`py-1 px-2 text-[9px] uppercase rounded-lg font-bold border cursor-pointer transition-colors ${
                      isFocused && focusHops === 3
                        ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] border-[var(--accent-blue)]'
                        : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/20 text-[var(--text-secondary)] border-[var(--border-color)]'
                    }`}
                  >
                    3 hops
                  </button>
                </>
              )}
              {onClearFocus && isFocused && (
                <button
                  onClick={onClearFocus}
                  className="ml-auto py-1 px-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-coral)]/20 text-[var(--text-secondary)] hover:text-[var(--accent-coral)] border border-[var(--border-color)] text-[9px] uppercase rounded-lg font-bold cursor-pointer flex items-center gap-1 transition-colors"
                >
                  <Focus className="w-3 h-3" />
                  Exit
                </button>
              )}
            </div>
          </div>
        )}

        <button
          onClick={() => {
            const dossierData: Record<string, any> = {
              "Subject": node.name,
              "Category": node.category.toUpperCase(),
              "Status": node.status?.replace(/_/g, ' ').toUpperCase() || 'UNKNOWN',
              "Risk Score": `${node.riskScore}%`,
              "Linked Cases": node.casesCount,
              "Details": node.details || 'N/A',
            };
            if (node.phone) dossierData["Phone"] = node.phone;
            if (node.gangAffiliation) dossierData["Gang"] = node.gangAffiliation;
            if (node.district) dossierData["District"] = node.district;
            dossierData["Source"] = node.isSeed ? 'Demo seed' : 'Live database';
            downloadSecureDossier(`${node.name} dossier`, dossierData, user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL');
            if (user) addLog(user.name, user.badgeId, 'EXPORT', `Exported dossier for ${node.name}`);
          }}
          className="w-full py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-white text-[11px] uppercase rounded-lg font-bold cursor-pointer flex items-center justify-center gap-1.5 transition-colors"
        >
          <FileText className="w-3.5 h-3.5" />
          Export Dossier
        </button>
        <button
          onClick={() => {
            const matrixData: Record<string, any> = {
              "Entity": `${node.name} (${node.category.toUpperCase()})`,
              "Connections": connectedNodes.map(({ otherName, link }) => `${otherName} — ${link.relationship}`),
              "Source": node.isSeed ? 'Demo seed' : 'Live database',
            };
            downloadSecureDossier(`${node.name} connections`, matrixData, user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL');
            if (user) addLog(user.name, user.badgeId, 'EXPORT', `Exported connections for ${node.name}`);
          }}
          className="w-full py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-[11px] uppercase rounded-lg font-semibold border border-[var(--border-color)] cursor-pointer flex items-center justify-center gap-1.5 transition-colors"
        >
          <Share2 className="w-3.5 h-3.5" />
          Export Connections
        </button>
      </div>
    </div>
  );
};
export default NodeDetailPanel;
