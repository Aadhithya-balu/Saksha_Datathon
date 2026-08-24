import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Cell,
} from 'recharts';
import { motion } from 'framer-motion';
import {
  Shield, TrendingUp, TrendingDown, Minus, AlertTriangle, MapPin,
  Users, FileText, Target, Brain, Clock, Activity, Loader2, ChevronRight,
  Zap, Radio, Flame,
} from 'lucide-react';
import {
  getStrategicBriefing, getDailySummary, getResourceAllocation, getStrategicEmergingTrends,
  type StrategicBriefing, type DailySummary, type ResourceAllocation,
} from '../../services/api';

const COLORS = ['#C94A2A', '#D4820A', '#1E6FD9', '#0D9488', '#7C3AED', '#EC4899', '#64748B', '#059669'];

export default function Strategic() {
  const [briefing, setBriefing] = useState<StrategicBriefing | null>(null);
  const [daily, setDaily] = useState<DailySummary | null>(null);
  const [resources, setResources] = useState<ResourceAllocation | null>(null);
  const [emergingTrends, setEmergingTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string>('command');
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [b, d, r, t] = await Promise.allSettled([
        getStrategicBriefing(),
        getDailySummary(),
        getResourceAllocation(),
        getStrategicEmergingTrends(),
      ]);
      if (b.status === 'fulfilled') setBriefing(b.value);
      if (d.status === 'fulfilled') setDaily(d.value);
      if (r.status === 'fulfilled') setResources(r.value);
      if (t.status === 'fulfilled' && Array.isArray(t.value)) setEmergingTrends(t.value);
    } catch (e) {
      console.error('Failed to load strategic data', e);
      setLoadError('Failed to load strategic briefing data. Please try again.');
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
        <span className="ml-3 text-[var(--text-secondary)]">Generating strategic briefing...</span>
      </div>
    );
  }

  if (loadError && !briefing && !daily && !resources) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <div className="w-12 h-12 rounded-xl bg-[var(--accent-coral-subtle)] border border-[var(--accent-coral)]/20 flex items-center justify-center">
          <Shield className="w-6 h-6 text-[var(--accent-coral)]" />
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{loadError}</p>
        <button onClick={() => { setLoadError(null); loadData(); }}
          className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm hover:opacity-90 transition">
          Retry
        </button>
      </div>
    );
  }

  const s = briefing?.summary;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Strategic Intelligence Command</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            High-level intelligence briefing for command staff &middot; {briefing?.generated_at ? new Date(briefing.generated_at).toLocaleString() : ''}
          </p>
        </div>
        <button onClick={loadData} className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm hover:opacity-90 transition">
          Refresh Briefing
        </button>
      </div>

      {/* Daily Intelligence Banner */}
      {daily && (
        <div className="p-4 bg-gradient-to-r from-[var(--accent-blue)]/10 to-[var(--accent-teal)]/10 rounded-xl border border-[var(--accent-blue)]/20">
          <div className="flex items-center gap-3 mb-3">
            <Radio className="w-5 h-5 text-[var(--accent-blue)]" />
            <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Daily Intelligence Summary &mdash; {daily.date}</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <MiniStat label="Today's Crimes" value={daily.today_crimes} trend={daily.trend} />
            <MiniStat label="Yesterday" value={daily.yesterday_crimes} />
            <MiniStat label="FIRs Filed" value={daily.today_firs} />
            <MiniStat label="Open Cases" value={daily.open_cases} />
            <MiniStat label="At Large" value={daily.at_large_criminals} alert />
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--bg-secondary)] rounded-lg overflow-x-auto">
        {[
          { id: 'command', label: 'Command Overview', icon: Shield },
          { id: 'risk', label: 'Risk Districts', icon: AlertTriangle },
          { id: 'trends', label: 'Emerging Trends', icon: TrendingUp },
          { id: 'deployment', label: 'Deployment', icon: Target },
          { id: 'network', label: 'Top Networks', icon: Users },
        ].map((tab) => (
          <button key={tab.id} onClick={() => setActiveSection(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              activeSection === tab.id
                ? 'bg-[var(--accent-blue)] text-white shadow-md'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
            }`}>
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Command Overview */}
      {activeSection === 'command' && s && (
        <div className="space-y-6">
          {/* KPI Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <KPICard label="Total Crimes" value={s.total_crimes} icon={Activity} color="#1E6FD9" />
            <KPICard label="Open Cases" value={s.open_cases} icon={FileText} color="#D4820A" />
            <KPICard label="Resolution Rate" value={`${s.resolution_rate}%`} icon={Target} color="#0D9488" />
            <KPICard label="At Large" value={s.at_large_criminals} icon={AlertTriangle} color="#C94A2A" />
            <KPICard label="Trend (30d)" value={`${s.crime_trend_change > 0 ? '+' : ''}${s.crime_trend_change}%`}
              icon={s.crime_trend_change > 0 ? TrendingUp : s.crime_trend_change < 0 ? TrendingDown : Minus}
              color={s.crime_trend_change > 0 ? '#C94A2A' : '#0D9488'} />
            <KPICard label="30-Day Crimes" value={s.recent_crimes_30d} icon={Clock} color="#7C3AED" />
            <KPICard label="Weekly Crimes" value={s.weekly_crimes} icon={Zap} color="#EC4899" />
            <KPICard label="High Priority" value={s.high_priority_cases} icon={AlertTriangle} color="#C94A2A" />
            <KPICard label="Pending Evidence" value={s.pending_evidence} icon={FileText} color="#D4820A" />
            <KPICard label="Active Officers" value={s.total_officers} icon={Users} color="#1E6FD9" />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Categories */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
                <AlertTriangle className="w-4 h-4 text-[var(--accent-coral)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Top Crime Categories</h3>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={briefing?.top_categories || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                    <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                    <YAxis type="category" dataKey="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={120} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {(briefing?.top_categories || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Monthly Trend */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
                <TrendingUp className="w-4 h-4 text-[var(--accent-blue)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Monthly Crime Trend</h3>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={briefing?.monthly_trend || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                    <XAxis dataKey="month" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                    <Line type="monotone" dataKey="count" stroke="#1E6FD9" strokeWidth={2} dot={{ fill: '#1E6FD9', r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Districts */}
      {activeSection === 'risk' && briefing?.districts_at_risk && (
        <div className="space-y-4">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
              <MapPin className="w-4 h-4 text-[var(--accent-coral)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">District Risk Assessment</h3>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {briefing.districts_at_risk.map((d) => (
                  <div key={d.district} className={`p-4 rounded-lg border ${
                    d.risk_level === 'CRITICAL' ? 'border-red-500/40 bg-red-500/5' :
                    d.risk_level === 'HIGH' ? 'border-amber-500/40 bg-amber-500/5' :
                    'border-[var(--border-primary)] bg-[var(--bg-primary)]'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-bold text-[var(--text-primary)]">{d.district}</h4>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        d.risk_level === 'CRITICAL' ? 'bg-red-500/20 text-red-400' :
                        d.risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-400' :
                        d.risk_level === 'MEDIUM' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>{d.risk_level}</span>
                    </div>
                    <div className="text-2xl font-bold text-[var(--text-primary)] mb-1">{d.crime_count} <span className="text-xs font-normal text-[var(--text-muted)]">crimes</span></div>
                    {d.factors.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {d.factors.map((f, i) => (
                          <div key={i} className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                            <span className="w-1 h-1 rounded-full bg-[var(--accent-coral)]" />
                            {f}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Emerging Trends */}
      {activeSection === 'trends' && (
        <div className="space-y-4">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-primary)]">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-[var(--accent-purple)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Emerging Crime Trends (30-day Spatiotemporal Comparison)
                </h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-500/10 text-red-400 border border-red-500/30 flex items-center gap-1">
                <Flame className="w-3 h-3 text-red-400 animate-pulse" />
                Live Surge Telemetry
              </span>
            </div>
            <div className="p-4">
              <div className="space-y-3">
                {(emergingTrends.length > 0 ? emergingTrends : (briefing?.emerging_trends || [])).map((t: any) => {
                  const isSpike = t.direction === 'increasing' && t.change_percentage > 10;
                  return (
                    <div 
                      key={t.category} 
                      className={`flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg border transition-all gap-3 ${
                        isSpike 
                          ? 'bg-red-500/5 border-red-500/30 hover:border-red-500/60 shadow-sm' 
                          : 'bg-[var(--bg-primary)] border-[var(--border-primary)]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2.5 h-10 rounded-full ${
                          isSpike ? 'bg-red-500 animate-pulse' :
                          t.direction === 'increasing' ? 'bg-[var(--accent-coral)]' :
                          t.direction === 'decreasing' ? 'bg-[var(--accent-teal)]' : 'bg-[var(--text-muted)]'
                        }`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-[var(--text-primary)]">{t.category}</h4>
                            {isSpike && (
                              <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-[9px] font-bold uppercase flex items-center gap-1 border border-red-500/40 animate-pulse">
                                <Flame className="w-2.5 h-2.5" />
                                Red-Zone Surge
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-[var(--text-muted)] mt-0.5 font-mono">
                            {t.recent_count} recent filings vs {t.historical_count} baseline filings
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 self-end sm:self-center">
                        <div className="text-right">
                          <span className={`text-lg font-mono font-extrabold flex items-center gap-1 justify-end ${
                            isSpike ? 'text-red-400' :
                            t.direction === 'increasing' ? 'text-[var(--accent-coral)]' :
                            t.direction === 'decreasing' ? 'text-[var(--accent-teal)]' : 'text-[var(--text-muted)]'
                          }`}>
                            {t.change_percentage > 0 ? '+' : ''}{t.change_percentage}%
                            {t.direction === 'increasing' ? <TrendingUp className="w-5 h-5 text-red-400" /> :
                             t.direction === 'decreasing' ? <TrendingDown className="w-5 h-5 text-[var(--accent-teal)]" /> :
                             <Minus className="w-5 h-5 text-[var(--text-muted)]" />}
                          </span>
                          <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase">
                            {t.direction} trajectory
                          </span>
                        </div>

                        <button
                          onClick={() => {
                            window.dispatchEvent(new CustomEvent('navigate-tab', { detail: 'hotspot' }));
                          }}
                          className="px-3 py-1.5 bg-[var(--accent-blue)]/10 hover:bg-[var(--accent-blue)]/20 border border-[var(--accent-blue)]/30 text-[var(--accent-blue)] text-xs font-mono font-bold rounded-btn transition-colors cursor-pointer flex items-center gap-1"
                          title="Locate this surge on the Spatiotemporal Hotspots Vector Map"
                        >
                          <span>Locate on Map</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Deployment */}
      {activeSection === 'deployment' && briefing?.deployment_suggestions && (
        <div className="space-y-4">
          {resources?.allocations && (
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
                <Target className="w-4 h-4 text-[var(--accent-teal)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Resource Allocation by District</h3>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={resources.allocations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                    <XAxis dataKey="district" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} angle={-30} textAnchor="end" height={80} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                    <Bar dataKey="crime_share_pct" name="Crime Share %" radius={[4, 4, 0, 0]}>
                      {resources.allocations.map((entry, i) => (
                        <Cell key={i} fill={entry.allocation_priority === 'CRITICAL' ? '#C94A2A' : entry.allocation_priority === 'HIGH' ? '#D4820A' : '#1E6FD9'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
              <Zap className="w-4 h-4 text-[var(--accent-amber)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Recommended Actions</h3>
            </div>
            <div className="p-4 space-y-3">
              {briefing.deployment_suggestions.map((sug, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-primary)]">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    sug.priority === 'CRITICAL' ? 'bg-red-500/20' : sug.priority === 'HIGH' ? 'bg-amber-500/20' : 'bg-blue-500/20'
                  }`}>
                    {sug.priority === 'CRITICAL' ? <AlertTriangle className="w-4 h-4 text-red-400" /> :
                     sug.priority === 'HIGH' ? <Zap className="w-4 h-4 text-amber-400" /> :
                     <Activity className="w-4 h-4 text-blue-400" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        sug.priority === 'CRITICAL' ? 'bg-red-500/20 text-red-400' :
                        sug.priority === 'HIGH' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
                      }`}>{sug.priority}</span>
                      <span className="text-xs text-[var(--text-muted)]">{sug.district}</span>
                    </div>
                    <h4 className="text-sm font-semibold text-[var(--text-primary)] mt-1">{sug.action}</h4>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{sug.reason}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[var(--text-muted)] mt-2" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top Networks */}
      {activeSection === 'network' && briefing?.top_criminals && (
        <div className="space-y-4">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
              <Users className="w-4 h-4 text-[var(--accent-coral)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Most Active Offenders</h3>
            </div>
            <div className="p-4">
              <div className="space-y-3">
                {briefing.top_criminals.map((c, i) => (
                  <div key={c.id} className="flex items-center gap-4 p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-primary)]">
                    <div className="w-10 h-10 rounded-full bg-[var(--accent-coral)]/10 flex items-center justify-center text-[var(--accent-coral)] font-bold text-sm">
                      #{i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-[var(--text-primary)]">{c.name}</h4>
                      {c.aliases && <p className="text-xs text-[var(--text-muted)]">Alias: {c.aliases}</p>}
                      {c.risk_factors && <p className="text-xs text-[var(--text-muted)] mt-1 line-clamp-1">{c.risk_factors}</p>}
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      c.status === 'at_large' ? 'bg-red-500/20 text-red-400' :
                      c.status === 'arrested' ? 'bg-amber-500/20 text-amber-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>{c.status.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent FIRs */}
          {briefing.recent_firs.length > 0 && (
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
                <FileText className="w-4 h-4 text-[var(--accent-blue)]" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Recent FIRs</h3>
              </div>
              <div className="p-4 space-y-2">
                {briefing.recent_firs.map((f) => (
                  <div key={f.id} className="flex items-center justify-between p-2.5 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-primary)]">
                    <div>
                      <span className="text-sm font-mono font-semibold text-[var(--accent-blue)]">{f.fir_number}</span>
                      <span className="text-xs text-[var(--text-muted)] ml-3">{f.complainant}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        f.status === 'open' ? 'bg-amber-500/20 text-amber-400' : 'bg-green-500/20 text-green-400'
                      }`}>{f.status}</span>
                      {f.filed_at && <span className="text-xs text-[var(--text-muted)]">{new Date(f.filed_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

function KPICard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: any; color: string }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)]">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <div>
          <div className="text-xl font-bold text-[var(--text-primary)]">{value}</div>
          <div className="text-xs text-[var(--text-muted)]">{label}</div>
        </div>
      </div>
    </motion.div>
  );
}

function MiniStat({ label, value, trend, alert }: { label: string; value: number; trend?: string; alert?: boolean }) {
  return (
    <div className="text-center">
      <div className={`text-xl font-bold ${alert ? 'text-[var(--accent-coral)]' : 'text-[var(--text-primary)]'}`}>{value}</div>
      <div className="text-xs text-[var(--text-muted)]">{label}</div>
      {trend && (
        <div className={`text-[10px] mt-0.5 font-medium ${
          trend === 'increasing' ? 'text-[var(--accent-coral)]' : trend === 'decreasing' ? 'text-[var(--accent-teal)]' : 'text-[var(--text-muted)]'
        }`}>
          {trend === 'increasing' ? '↑' : trend === 'decreasing' ? '↓' : '—'} {trend}
        </div>
      )}
    </div>
  );
}
