import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter, Legend, LineChart, Line, Area, AreaChart,
} from 'recharts';
import { motion } from 'framer-motion';
import {
  Users, MapPin, TrendingUp, Brain, Clock, AlertTriangle, Activity, Building2,
  ChevronDown, ChevronUp, Info, Loader2,
} from 'lucide-react';
import {
  getSociologicalDemographics, getSociologicalUrbanRural, getSociologicalSocioeconomic,
  getSociologicalPopulationCorrelation, getSociologicalTemporal, getSociologicalOffenderDemographics,
  type DemographicAnalysis, type UrbanRuralAnalysis, type SocioeconomicAnalysis,
  type ScatterPoint, type TemporalDemographic, type OffenderDemographics,
} from '../../services/api';

const COLORS = ['#C94A2A', '#D4820A', '#1E6FD9', '#0D9488', '#7C3AED', '#EC4899', '#64748B', '#059669'];

export default function Sociological() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [demographics, setDemographics] = useState<DemographicAnalysis | null>(null);
  const [urbanRural, setUrbanRural] = useState<UrbanRuralAnalysis | null>(null);
  const [socioeconomic, setSocioeconomic] = useState<SocioeconomicAnalysis | null>(null);
  const [population, setPopulation] = useState<{ scatter: ScatterPoint[]; total_districts: number } | null>(null);
  const [temporal, setTemporal] = useState<TemporalDemographic | null>(null);
  const [offenderDemo, setOffenderDemo] = useState<OffenderDemographics | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedInsight, setExpandedInsight] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  async function loadAllData() {
    setLoading(true);
    try {
      const [d, u, s, p, t, o] = await Promise.allSettled([
        getSociologicalDemographics(),
        getSociologicalUrbanRural(),
        getSociologicalSocioeconomic(),
        getSociologicalPopulationCorrelation(),
        getSociologicalTemporal(),
        getSociologicalOffenderDemographics(),
      ]);
      if (d.status === 'fulfilled') setDemographics(d.value);
      if (u.status === 'fulfilled') setUrbanRural(u.value);
      if (s.status === 'fulfilled') setSocioeconomic(s.value);
      if (p.status === 'fulfilled') setPopulation(p.value);
      if (t.status === 'fulfilled') setTemporal(t.value);
      if (o.status === 'fulfilled') setOffenderDemo(o.value);
    } catch (e) {
      console.error('Failed to load sociological data', e);
      setLoadError('Failed to load sociological intelligence data. Please try again.');
    }
    setLoading(false);
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'demographics', label: 'Demographics', icon: Users },
    { id: 'geographic', label: 'Geographic', icon: MapPin },
    { id: 'socioeconomic', label: 'Socio-Economic', icon: TrendingUp },
    { id: 'temporal', label: 'Temporal', icon: Clock },
    { id: 'offenders', label: 'Offender Profile', icon: AlertTriangle },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-blue)]" />
        <span className="ml-3 text-[var(--text-secondary)]">Loading sociological intelligence...</span>
      </div>
    );
  }

  if (loadError && !demographics && !urbanRural && !socioeconomic) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <div className="w-12 h-12 rounded-xl bg-[var(--accent-coral-subtle)] border border-[var(--accent-coral)]/20 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-[var(--accent-coral)]" />
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{loadError}</p>
        <button onClick={() => { setLoadError(null); loadAllData(); }}
          className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm hover:opacity-90 transition">
          Retry
        </button>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
      className="space-y-6">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Sociological Intelligence</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Demographic, geographic, and socio-economic crime correlation analysis
          </p>
        </div>
        <button onClick={loadAllData}
          className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg text-sm hover:opacity-90 transition">
          Refresh Data
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-[var(--bg-secondary)] rounded-lg overflow-x-auto">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              activeTab === tab.id
                ? 'bg-[var(--accent-blue)] text-white shadow-md'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
            }`}>
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <SummaryCard icon={Users} label="Total Victims" value={demographics?.total_victims || 0} color="#1E6FD9" />
            <SummaryCard icon={AlertTriangle} label="Total Offenders" value={offenderDemo?.total_offenders || 0} color="#C94A2A" />
            <SummaryCard icon={MapPin} label="Districts Tracked" value={population?.total_districts || 0} color="#0D9488" />
            <SummaryCard icon={Brain} label="AI Insights" value={socioeconomic?.insights?.length || 0} color="#7C3AED" />
          </div>

          {/* Urban vs Rural + Night Crime */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="Urban vs Rural Crime Distribution" icon={Building2}>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={urbanRural?.urban_rural_distribution || []} dataKey="count" nameKey="label"
                    cx="50%" cy="50%" outerRadius={90} label={({ label, percentage }) => `${label}: ${percentage}%`}>
                    {(urbanRural?.urban_rural_distribution || []).map((entry, i) => (
                      <Cell key={i} fill={entry.color || COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Night vs Day Crime" icon={Clock}>
              <div className="flex items-center justify-center h-[280px]">
                <div className="text-center space-y-4">
                  <div className="relative w-40 h-40 mx-auto">
                    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-tertiary)" strokeWidth="12" />
                      <circle cx="50" cy="50" r="40" fill="none" stroke="#C94A2A" strokeWidth="12"
                        strokeDasharray={`${(temporal?.night_crime_percentage || 0) * 2.51} 251`} strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl font-bold text-[var(--text-primary)]">{temporal?.night_crime_percentage || 0}%</span>
                    </div>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">Crimes occur during night hours (8PM - 5AM)</p>
                  <div className="flex justify-center gap-6 text-sm">
                    <div><span className="text-[var(--accent-coral)] font-bold">{temporal?.night_crime_percentage || 0}%</span> <span className="text-[var(--text-muted)]">Night</span></div>
                    <div><span className="text-[var(--accent-blue)] font-bold">{100 - (temporal?.night_crime_percentage || 0)}%</span> <span className="text-[var(--text-muted)]">Day</span></div>
                  </div>
                </div>
              </div>
            </ChartCard>
          </div>

          {/* AI Insights */}
          {socioeconomic?.insights && socioeconomic.insights.length > 0 && (
            <ChartCard title="AI Socio-Economic Insights" icon={Brain}>
              <div className="space-y-3 p-4">
                {socioeconomic.insights.map((insight, i) => (
                  <div key={i} className="p-3 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-primary)]">
                    <div className="flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                        insight.type === 'high_risk_district' ? 'bg-[var(--accent-coral)]' :
                        insight.type === 'economic_correlation' ? 'bg-[var(--accent-amber)]' :
                        insight.type === 'urban_crime' ? 'bg-[var(--accent-blue)]' : 'bg-[var(--accent-teal)]'
                      }`} />
                      <div>
                        <h4 className="text-sm font-semibold text-[var(--text-primary)]">{insight.title}</h4>
                        <p className="text-xs text-[var(--text-secondary)] mt-1">{insight.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}

          {/* Correlation Scores */}
          {socioeconomic?.correlations && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)]">
                <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Literacy vs Crime Correlation</h4>
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-bold text-[var(--accent-blue)]">
                    {socioeconomic.correlations.literacy_vs_crime}
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    {socioeconomic.correlations.literacy_vs_crime < -0.3
                      ? 'Negative correlation: Higher literacy → Lower crime'
                      : socioeconomic.correlations.literacy_vs_crime > 0.3
                      ? 'Positive correlation detected'
                      : 'Weak correlation'}
                  </div>
                </div>
              </div>
              <div className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)]">
                <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Income vs Crime Correlation</h4>
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-bold text-[var(--accent-amber)]">
                    {socioeconomic.correlations.income_vs_crime}
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    {socioeconomic.correlations.income_vs_crime < -0.3
                      ? 'Negative correlation: Higher income → Lower crime'
                      : socioeconomic.correlations.income_vs_crime > 0.3
                      ? 'Positive correlation detected'
                      : 'Weak correlation'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Demographics Tab */}
      {activeTab === 'demographics' && demographics && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="Victim Age Distribution" icon={Users}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={demographics.age_groups}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                  <XAxis dataKey="group" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                  <Bar dataKey="count" name="Victims" radius={[4, 4, 0, 0]}>
                    {demographics.age_groups.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Victim Gender Distribution" icon={Users}>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={demographics.gender_distribution} dataKey="count" nameKey="gender"
                    cx="50%" cy="50%" outerRadius={100}
                    label={({ gender, percentage }) => `${gender}: ${percentage}%`}>
                    {demographics.gender_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </div>
      )}

      {/* Geographic Tab */}
      {activeTab === 'geographic' && (
        <div className="space-y-6">
          {/* Population vs Crime Scatter */}
          {population?.scatter && (
            <ChartCard title="Crime Rate vs Population Density" icon={MapPin}>
              <ResponsiveContainer width="100%" height={350}>
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                  <XAxis type="number" dataKey="population_density" name="Pop Density"
                    tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                    label={{ value: 'Population Density (/sq km)', position: 'bottom', fill: 'var(--text-muted)', fontSize: 12 }} />
                  <YAxis type="number" dataKey="crime_per_lakh" name="Crime Rate"
                    tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                    label={{ value: 'Crime per Lakh', angle: -90, position: 'left', fill: 'var(--text-muted)', fontSize: 12 }} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }}
                    contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }}
                    formatter={(value: any, name: string) => [value, name === 'Pop Density' ? 'Pop Density' : name === 'Crime Rate' ? 'Crime/Lakh' : name]}
                    labelFormatter={() => ''} />
                  <Scatter data={population.scatter} fill="#1E6FD9">
                    {population.scatter.map((entry, i) => (
                      <Cell key={i} fill={entry.color || COLORS[i % COLORS.length]} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-6 mt-2 text-xs text-[var(--text-muted)]">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-[#C94A2A] inline-block" /> Urban</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-[#D4820A] inline-block" /> Semi-Urban</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-[#1E6FD9] inline-block" /> Rural</span>
              </div>
            </ChartCard>
          )}

          {/* District Crime Density Table */}
          {urbanRural?.district_crime_density && (
            <ChartCard title="District Crime Density Ranking" icon={MapPin}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-primary)]">
                      <th className="text-left py-3 px-3 text-[var(--text-muted)] font-medium">#</th>
                      <th className="text-left py-3 px-3 text-[var(--text-muted)] font-medium">District</th>
                      <th className="text-left py-3 px-3 text-[var(--text-muted)] font-medium">Type</th>
                      <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Crimes</th>
                      <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Per Lakh</th>
                      <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Per Sq Km</th>
                      <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Population</th>
                    </tr>
                  </thead>
                  <tbody>
                    {urbanRural.district_crime_density.map((d, i) => (
                      <tr key={d.district} className="border-b border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]">
                        <td className="py-2.5 px-3 text-[var(--text-muted)]">{i + 1}</td>
                        <td className="py-2.5 px-3 text-[var(--text-primary)] font-medium">{d.district}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            d.type === 'urban' ? 'bg-red-500/20 text-red-400' :
                            d.type === 'semi_urban' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-blue-500/20 text-blue-400'
                          }`}>
                            {d.type === 'urban' ? 'Urban' : d.type === 'semi_urban' ? 'Semi-Urban' : 'Rural'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-primary)]">{d.crime_count}</td>
                        <td className="py-2.5 px-3 text-right text-[var(--accent-coral)] font-medium">{d.crime_per_lakh}</td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{d.crime_per_sqkm}</td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{d.population_lakhs}L</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          )}
        </div>
      )}

      {/* Socio-Economic Tab */}
      {activeTab === 'socioeconomic' && socioeconomic && (
        <div className="space-y-6">
          {/* District Socio-Economic Overlay */}
          <ChartCard title="District Socio-Economic Overlay" icon={TrendingUp}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-primary)]">
                    <th className="text-left py-3 px-3 text-[var(--text-muted)] font-medium">District</th>
                    <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Crime/Lakh</th>
                    <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Literacy %</th>
                    <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Sex Ratio</th>
                    <th className="text-right py-3 px-3 text-[var(--text-muted)] font-medium">Avg Income (L)</th>
                    <th className="text-left py-3 px-3 text-[var(--text-muted)] font-medium">Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {socioeconomic.districts.map((d) => (
                    <tr key={d.district} className="border-b border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]">
                      <td className="py-2.5 px-3 text-[var(--text-primary)] font-medium">{d.district}</td>
                      <td className="py-2.5 px-3 text-right text-[var(--accent-coral)] font-bold">{d.crime_per_lakh}</td>
                      <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{d.literacy_rate}%</td>
                      <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">{d.sex_ratio}</td>
                      <td className="py-2.5 px-3 text-right text-[var(--accent-amber)]">{d.avg_income_lakhs}</td>
                      <td className="py-2.5 px-3">
                        <div className="flex gap-1 flex-wrap">
                          {d.correlation_flags.map((flag) => (
                            <span key={flag} className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                              flag.includes('HIGH') ? 'bg-red-500/20 text-red-400' :
                              flag.includes('LOW') ? 'bg-amber-500/20 text-amber-400' :
                              'bg-blue-500/20 text-blue-400'
                            }`}>
                              {flag.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>

          {/* Insights */}
          {socioeconomic.insights.length > 0 && (
            <ChartCard title="Socio-Economic Intelligence Insights" icon={Brain}>
              <div className="space-y-3 p-4">
                {socioeconomic.insights.map((insight, i) => (
                  <div key={i} className="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-primary)] cursor-pointer hover:border-[var(--accent-blue)] transition"
                    onClick={() => setExpandedInsight(expandedInsight === i ? null : i)}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className={`w-5 h-5 ${
                          insight.type === 'high_risk_district' ? 'text-[var(--accent-coral)]' :
                          insight.type === 'economic_correlation' ? 'text-[var(--accent-amber)]' :
                          'text-[var(--accent-blue)]'
                        }`} />
                        <h4 className="text-sm font-semibold text-[var(--text-primary)]">{insight.title}</h4>
                      </div>
                      {expandedInsight === i ? <ChevronUp className="w-4 h-4 text-[var(--text-muted)]" /> : <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />}
                    </div>
                    {expandedInsight === i && (
                      <p className="text-xs text-[var(--text-secondary)] mt-2 ml-8">{insight.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>
      )}

      {/* Temporal Tab */}
      {activeTab === 'temporal' && temporal && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="Crime by Hour of Day" icon={Clock}>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={temporal.hourly_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                  <XAxis dataKey="hour" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} interval={2} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                  <Area type="monotone" dataKey="count" stroke="#C94A2A" fill="#C94A2A" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Crime by Day of Week" icon={Clock}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={temporal.day_of_week_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                  <XAxis dataKey="day" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                  <Bar dataKey="count" name="Crimes" radius={[4, 4, 0, 0]}>
                    {temporal.day_of_week_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <ChartCard title="Monthly Crime Trend" icon={TrendingUp}>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={temporal.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                <XAxis dataKey="month" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                <Line type="monotone" dataKey="count" stroke="#1E6FD9" strokeWidth={2} dot={{ fill: '#1E6FD9', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] text-center">
              <div className="text-2xl font-bold text-[var(--accent-coral)]">{temporal.night_crime_percentage}%</div>
              <div className="text-xs text-[var(--text-muted)] mt-1">Night Crime Rate</div>
            </div>
            <div className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] text-center">
              <div className="text-2xl font-bold text-[var(--accent-blue)]">{temporal.weekend_crime_percentage}%</div>
              <div className="text-xs text-[var(--text-muted)] mt-1">Weekend Crime Rate</div>
            </div>
          </div>
        </div>
      )}

      {/* Offender Profile Tab */}
      {activeTab === 'offenders' && offenderDemo && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="Offender Age Distribution" icon={AlertTriangle}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={offenderDemo.age_groups}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                  <XAxis dataKey="group" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                  <Bar dataKey="count" name="Offenders" radius={[4, 4, 0, 0]}>
                    {offenderDemo.age_groups.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Offender Status" icon={AlertTriangle}>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={offenderDemo.status_distribution} dataKey="count" nameKey="status"
                    cx="50%" cy="50%" outerRadius={100}
                    label={({ status, percentage }) => `${status.replace('_', ' ')}: ${percentage}%`}>
                    {offenderDemo.status_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <ChartCard title="Offender Gender Distribution" icon={Users}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={offenderDemo.gender_distribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <YAxis type="category" dataKey="gender" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} width={80} />
                <Tooltip contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 8 }} />
                <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                  {offenderDemo.gender_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}
    </motion.div>
  );
}

function SummaryCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)]">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <div>
          <div className="text-2xl font-bold text-[var(--text-primary)]">{value}</div>
          <div className="text-xs text-[var(--text-muted)]">{label}</div>
        </div>
      </div>
    </motion.div>
  );
}

function ChartCard({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-primary)]">
        <Icon className="w-4 h-4 text-[var(--accent-blue)]" />
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}
