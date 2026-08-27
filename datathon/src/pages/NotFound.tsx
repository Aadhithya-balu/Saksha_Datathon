import { useEffect, useState } from 'react';
import {
  LayoutDashboard, Map, Brain, Network, Briefcase,
  FileText, Users, MessageSquare, AlertTriangle,
  ArrowLeft, Home, Search, Radio,
} from 'lucide-react';

const QUICK_LINKS = [
  { tab: 'dashboard',   label: 'Overview',      icon: <LayoutDashboard className="w-4 h-4" />, path: '/dashboard' },
  { tab: 'hotspot',     label: 'Hotspot Map',   icon: <Map className="w-4 h-4" />,             path: '/hotspots' },
  { tab: 'predictive',  label: 'Predictive AI', icon: <Brain className="w-4 h-4" />,           path: '/predictions' },
  { tab: 'network',     label: 'Network Graph', icon: <Network className="w-4 h-4" />,         path: '/network' },
  { tab: 'crime_cases', label: 'Crime Cases',   icon: <Briefcase className="w-4 h-4" />,       path: '/crime-cases' },
  { tab: 'fir',         label: 'FIR Registry',  icon: <FileText className="w-4 h-4" />,        path: '/firs' },
  { tab: 'criminals',   label: 'Criminals',     icon: <Users className="w-4 h-4" />,           path: '/criminals' },
  { tab: 'ai_chat',     label: 'AI Assistant',  icon: <MessageSquare className="w-4 h-4" />,   path: '/ai-chat' },
  { tab: 'anomaly',     label: 'Anomaly Feed',  icon: <AlertTriangle className="w-4 h-4" />,   path: '/anomalies' },
];

// Animated scanning line dots
function RadarPulse() {
  return (
    <div className="relative w-32 h-32 mx-auto mb-8">
      {/* Outer rings */}
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className="absolute inset-0 rounded-full border border-[var(--accent-blue)]/20 animate-ping"
          style={{ animationDelay: `${i * 0.4}s`, animationDuration: '2.4s' }}
        />
      ))}
      {/* Static rings */}
      <span className="absolute inset-0 rounded-full border border-[var(--accent-blue)]/10" />
      <span className="absolute inset-[18px] rounded-full border border-[var(--accent-blue)]/15" />
      <span className="absolute inset-[36px] rounded-full border border-[var(--accent-blue)]/20" />
      {/* Center icon */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-14 h-14 rounded-full bg-[var(--accent-blue-subtle)] border border-[var(--accent-blue)]/30 flex items-center justify-center">
          <Radio className="w-6 h-6 text-[var(--accent-blue)]" />
        </div>
      </div>
    </div>
  );
}

function NotFound() {
  const [typed, setTyped] = useState('');
  const headline = 'SIGNAL LOST';

  // Typewriter effect for headline
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      i++;
      setTyped(headline.slice(0, i));
      if (i >= headline.length) clearInterval(id);
    }, 80);
    return () => clearInterval(id);
  }, []);

  const navigate = (tab: string, _path: string) => {
    // The navigate-tab CustomEvent listener in App.tsx handles both
    // setActiveTab + URL sync, so we only dispatch the event here.
    window.dispatchEvent(new CustomEvent('navigate-tab', { detail: { tab } }));
  };

  const goBack = () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      navigate('dashboard', '/dashboard');
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 py-12">
      <div className="max-w-2xl w-full">

        {/* Radar animation */}
        <RadarPulse />

        {/* Error code */}
        <div className="text-center mb-2">
          <span className="inline-block font-mono text-xs tracking-[0.3em] text-[var(--accent-blue)] bg-[var(--accent-blue-subtle)] border border-[var(--accent-blue)]/20 px-3 py-1 rounded-full">
            ERROR · 404 · NOT FOUND
          </span>
        </div>

        {/* Typewriter headline */}
        <h1 className="text-center mt-4 text-3xl sm:text-4xl font-bold font-mono tracking-widest text-[var(--text-primary)] min-h-[2.5rem]">
          {typed}
          <span className="animate-pulse text-[var(--accent-blue)]">_</span>
        </h1>

        <p className="text-center mt-3 text-sm text-[var(--text-secondary)] max-w-md mx-auto">
          The intelligence module you requested could not be located. The route may have been
          decommissioned, relocated, or never existed in this system.
        </p>

        {/* Attempted path */}
        <div className="mt-4 flex items-center justify-center gap-2">
          <Search className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <code className="text-xs font-mono text-[var(--accent-coral)] bg-[var(--accent-coral-subtle)] px-2 py-0.5 rounded">
            {window.location.pathname}
          </code>
        </div>

        {/* Divider */}
        <div className="mt-8 mb-5 flex items-center gap-3">
          <div className="flex-1 h-px bg-[var(--border-primary)]" />
          <span className="text-[10px] font-mono tracking-widest text-[var(--text-disabled)] uppercase">Navigate to</span>
          <div className="flex-1 h-px bg-[var(--border-primary)]" />
        </div>

        {/* Quick-nav grid */}
        <div className="grid grid-cols-3 sm:grid-cols-3 gap-2">
          {QUICK_LINKS.map(({ tab, label, icon, path }) => (
            <button
              key={tab}
              onClick={() => navigate(tab, path)}
              className="flex flex-col items-center gap-1.5 p-3 rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] hover:border-[var(--accent-blue)]/40 hover:bg-[var(--accent-blue-subtle)] hover:text-[var(--accent-blue-light)] text-[var(--text-secondary)] transition-all duration-150 cursor-pointer group"
            >
              <span className="group-hover:scale-110 transition-transform duration-150">{icon}</span>
              <span className="text-[11px] font-medium text-center leading-tight">{label}</span>
            </button>
          ))}
        </div>

        {/* Action buttons */}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            onClick={goBack}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-secondary)] text-sm font-medium transition-all cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            Go Back
          </button>
          <button
            onClick={() => navigate('dashboard', '/dashboard')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-blue)] text-white hover:opacity-90 text-sm font-semibold transition-opacity cursor-pointer"
          >
            <Home className="w-4 h-4" />
            Dashboard
          </button>
        </div>

        {/* Footer stamp */}
        <p className="mt-8 text-center text-[10px] font-mono text-[var(--text-disabled)] tracking-widest uppercase">
          SAKSHA v2.0 · Karnataka State Police · SCRB
        </p>
      </div>
    </div>
  );
}

export default NotFound;
