import React, { useState } from 'react';
import {
  BookOpen,
  Search,
  LayoutDashboard,
  Briefcase,
  Users,
  Map,
  Network,
  Brain,
  MessageSquare,
  Bell,
  BarChart3,
  Settings,
  Shield,
  ChevronRight,
  ExternalLink,
  Zap,
  Target,
  FileText,
  FolderOpen,
  Heart,
  UserCog,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  Lightbulb,
  HelpCircle,
  Play,
  Eye,
  Clock,
  Workflow,
} from 'lucide-react';
import { SearchInput } from '../components/ui/SearchInput';
import { Badge } from '../components/ui/Badge';

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  category: string;
  content: React.ReactNode;
}

const sections: DocSection[] = [
  // Getting Started
  {
    id: 'what-is-saksha',
    title: 'What is Saksha?',
    icon: <Shield className="w-4 h-4" />,
    category: 'Getting Started',
    content: (
      <div className="space-y-4">
        <p className="text-[var(--text-secondary)] leading-relaxed">
          <strong className="text-[var(--text-primary)]">Saksha</strong> is a comprehensive Crime Intelligence & Analytical Platform developed for the <strong className="text-[var(--text-primary)]">Karnataka State Police (KSP)</strong> as part of Datathon 2026. It transforms raw crime records into actionable intelligence through AI/ML-powered analytics, graph-based criminal network analysis, and real-time notifications.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {[
            { icon: <Brain className="w-5 h-5 text-[var(--accent-blue)]" />, title: 'AI-Powered', desc: 'Predictive analytics, anomaly detection, and natural language queries' },
            { icon: <Network className="w-5 h-5 text-[var(--accent-purple)]" />, title: 'Graph Intelligence', desc: 'Visualize criminal networks, associations, and hidden connections' },
            { icon: <Zap className="w-5 h-5 text-[var(--accent-amber)]" />, title: 'Real-Time', desc: 'Live alerts, notifications, and dynamic dashboards' },
          ].map((f, i) => (
            <div key={i} className="sk-card p-4 text-center">
              <div className="w-10 h-10 rounded-xl bg-[var(--bg-tertiary)] flex items-center justify-center mx-auto mb-3">{f.icon}</div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{f.title}</h4>
              <p className="text-xs text-[var(--text-muted)]">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 'key-objectives',
    title: 'Key Objectives',
    icon: <Target className="w-4 h-4" />,
    category: 'Getting Started',
    content: (
      <div className="space-y-3">
        {[
          'Transform raw crime data into actionable intelligence for law enforcement',
          'Provide AI/ML-powered predictive analytics for crime hotspot identification',
          'Enable graph-based criminal network analysis and association mapping',
          'Deliver real-time notifications and alerts for active investigations',
          'Support data-driven decision making for policymakers and administrators',
          'Maintain a secure, role-based access control system for all users',
          'Generate comprehensive reports for legal proceedings and analysis',
        ].map((obj, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[var(--bg-tertiary)]/50">
            <CheckCircle className="w-4 h-4 text-[var(--accent-teal)] shrink-0 mt-0.5" />
            <span className="text-sm text-[var(--text-secondary)]">{obj}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    id: 'user-roles',
    title: 'User Roles & Access',
    icon: <Users className="w-4 h-4" />,
    category: 'Getting Started',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">Saksha supports 7 distinct user roles with different access levels:</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-primary)]">
                <th className="text-left py-2 px-3 text-[var(--text-muted)] font-medium">Role</th>
                <th className="text-left py-2 px-3 text-[var(--text-muted)] font-medium">Access Level</th>
              </tr>
            </thead>
            <tbody>
              {[
                { role: 'Admin', access: 'Full system access, user management, settings', variant: 'coral' as const },
                { role: 'Crime Analyst (SCRB)', access: 'All read routes, dashboard, AI analytics, reports', variant: 'blue' as const },
                { role: 'Investigator (IO)', access: 'CRUD for crimes, FIRs, criminals, victims, evidence', variant: 'teal' as const },
                { role: 'Inspector', access: 'Extended investigator + officer management', variant: 'purple' as const },
                { role: 'Policymaker (SP)', access: 'Read-only dashboard, AI analytics, reports', variant: 'amber' as const },
                { role: 'Officer', access: 'Basic read access + evidence handling', variant: 'info' as const },
                { role: 'Viewer', access: 'Read-only access to all modules', variant: 'default' as const },
              ].map((r, i) => (
                <tr key={i} className="border-b border-[var(--border-secondary)]">
                  <td className="py-2.5 px-3"><Badge variant={r.variant} size="sm">{r.role}</Badge></td>
                  <td className="py-2.5 px-3 text-[var(--text-secondary)]">{r.access}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    ),
  },
  // Platform Overview
  {
    id: 'architecture',
    title: 'System Architecture',
    icon: <LayoutDashboard className="w-4 h-4" />,
    category: 'Platform Overview',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">Saksha is built on a modern full-stack architecture:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { label: 'Frontend', tech: 'React 18 + TypeScript + Vite', desc: 'Single-page application with responsive design' },
            { label: 'Backend', tech: 'FastAPI (Python 3.12)', desc: 'RESTful API with 59+ endpoints' },
            { label: 'Database', tech: 'PostgreSQL 16 (Supabase)', desc: '16 relational tables for structured data' },
            { label: 'Graph DB', tech: 'Neo4j 5.24 (Aura)', desc: '8 node types, 7 relationship types for network analysis' },
            { label: 'AI/ML', tech: 'LightGBM, XGBoost, scikit-learn', desc: '8 AI algorithms for prediction and analysis' },
            { label: 'Authentication', tech: 'JWT + SHA-256', desc: 'Secure token-based auth with role-based access' },
          ].map((s, i) => (
            <div key={i} className="p-3 rounded-lg bg-[var(--bg-tertiary)]/50 border border-[var(--border-secondary)]">
              <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">{s.label}</div>
              <div className="text-sm font-semibold text-[var(--text-primary)]">{s.tech}</div>
              <div className="text-xs text-[var(--text-secondary)] mt-0.5">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 'ai-capabilities',
    title: 'AI Capabilities',
    icon: <Brain className="w-4 h-4" />,
    category: 'Platform Overview',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">Saksha integrates 8 distinct AI/ML algorithms:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { name: 'Crime Hotspot Prediction', algo: 'LightGBM + Optuna', desc: 'Predicts future crime hotspots using spatial and temporal features' },
            { name: 'District Risk Scoring', algo: 'RandomForest', desc: 'Scores districts by crime risk based on historical patterns' },
            { name: 'Crime Forecasting', algo: 'XGBoost/LightGBM', desc: 'Time-series forecasting of crime trends over 6-12 months' },
            { name: 'Criminal Risk Assessment', algo: 'Weighted Linear', desc: 'Calculates individual criminal risk scores from behavior patterns' },
            { name: 'Repeat Offender Prediction', algo: 'Logistic Regression', desc: 'Predicts likelihood of reoffending based on criminal history' },
            { name: 'Similar Offender Matching', algo: 'Cosine Similarity KNN', desc: 'Finds similar offenders based on crime patterns and MO' },
            { name: 'Criminal Clustering', algo: 'Mini k-means', desc: 'Groups criminals by behavioral patterns and connections' },
            { name: 'Anomaly Detection', algo: 'Z-score L2 Deviation', desc: 'Detects unusual patterns in crime data and officer activity' },
          ].map((a, i) => (
            <div key={i} className="p-3 rounded-lg bg-[var(--bg-tertiary)]/50 border border-[var(--border-secondary)]">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-[var(--text-primary)]">{a.name}</span>
              </div>
              <Badge variant="purple" size="xs">{a.algo}</Badge>
              <p className="text-xs text-[var(--text-muted)] mt-2">{a.desc}</p>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  // Module Guides
  {
    id: 'dashboard-guide',
    title: 'Dashboard',
    icon: <LayoutDashboard className="w-4 h-4" />,
    category: 'Module Guides',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          The Overview Dashboard is your command center, providing a real-time snapshot of crime intelligence across Karnataka.
        </p>
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">Key Features:</h4>
        <ul className="space-y-2">
          {[
            'KPI Cards: Total crimes, active cases, resolved cases, and officer count',
            'Crime Trend Chart: Monthly crime trend visualization with category breakdown',
            'Hotspot Map: Interactive spatial visualization of crime hotspots',
            'Forecast Chart: AI-predicted crime trends for the next 6 months',
            'Alert Feed: Real-time anomaly and critical alerts',
            'Risk Scores: District-level risk assessment with color-coded indicators',
          ].map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <ChevronRight className="w-3.5 h-3.5 text-[var(--accent-blue)] shrink-0 mt-1" />
              {f}
            </li>
          ))}
        </ul>
      </div>
    ),
  },
  {
    id: 'cases-guide',
    title: 'Crime Cases',
    icon: <Briefcase className="w-4 h-4" />,
    category: 'Module Guides',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          Crime Cases provides comprehensive case management for all registered criminal cases in Karnataka.
        </p>
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">What you can do:</h4>
        <ul className="space-y-2">
          {[
            'View and filter all crime cases by category, district, status, and priority',
            'Create new crime cases with linked FIRs, criminals, and victims',
            'Track case progress with visual progress indicators',
            'View case details including modus operandi, evidence, and investigation notes',
            'Access AI-powered case recommendations and insights',
          ].map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <ArrowRight className="w-3.5 h-3.5 text-[var(--accent-teal)] shrink-0 mt-1" />
              {f}
            </li>
          ))}
        </ul>
      </div>
    ),
  },
  {
    id: 'network-guide',
    title: 'Network Analysis',
    icon: <Network className="w-4 h-4" />,
    category: 'Module Guides',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          The Network Graph module provides 3D visualization of criminal networks and associations stored in Neo4j.
        </p>
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">Capabilities:</h4>
        <ul className="space-y-2">
          {[
            'Interactive 3D graph visualization with force-directed layout',
            'Explore criminal associations, gang networks, and known associates',
            'Shortest path analysis between any two entities',
            'Link analysis for discovering hidden connections',
            'AI-powered graph insights for pattern detection',
            'Timeline slider to see network evolution over time',
          ].map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
              <Network className="w-3.5 h-3.5 text-[var(--accent-purple)] shrink-0 mt-1" />
              {f}
            </li>
          ))}
        </ul>
      </div>
    ),
  },
  {
    id: 'ai-chat-guide',
    title: 'AI Assistant',
    icon: <MessageSquare className="w-4 h-4" />,
    category: 'Module Guides',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          The AI Chat Assistant provides natural language access to crime data and analytics. Ask questions in plain English and get instant answers.
        </p>
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">Example Queries:</h4>
        <div className="space-y-2">
          {[
            { q: '"Show me all cyber crimes in Bengaluru"', desc: 'Returns filtered case data' },
            { q: '"What is the risk score for district Mysuru?"', desc: 'AI risk assessment lookup' },
            { q: '"Who are the known associates of Ramu Swamy?"', desc: 'Network graph query' },
            { q: '"Predict crime hotspots for next quarter"', desc: 'AI prediction with visualization' },
            { q: '"Generate a summary report for FIR-2026-001"', desc: 'Automated report generation' },
          ].map((ex, i) => (
            <div key={i} className="p-3 rounded-lg bg-[var(--bg-tertiary)]/50 border border-[var(--border-secondary)]">
              <div className="text-sm font-medium text-[var(--text-primary)] font-mono">{ex.q}</div>
              <div className="text-xs text-[var(--text-muted)] mt-1">{ex.desc}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 rounded-lg bg-[var(--accent-amber-subtle)] border border-[var(--accent-amber)]/20">
          <div className="flex items-start gap-2">
            <Lightbulb className="w-4 h-4 text-[var(--accent-amber)] shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-[var(--text-primary)]">Tip</div>
              <div className="text-xs text-[var(--text-secondary)] mt-0.5">The AI Assistant uses RAG (Retrieval-Augmented Generation) to search case data, criminal records, and analytics before generating responses. All answers include source citations.</div>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'investigation-workflow',
    title: 'Investigation Workflow',
    icon: <Workflow className="w-4 h-4" />,
    category: 'Module Guides',
    content: (
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">The end-to-end investigation process in Saksha:</p>
        <div className="space-y-0">
          {[
            { step: 'Crime Registration', desc: 'Report filed as FIR, linked to crime case', icon: <FileText className="w-4 h-4" />, color: 'var(--accent-blue)' },
            { step: 'Investigation', desc: 'IO assigned, evidence collected, timeline tracked', icon: <Search className="w-4 h-4" />, color: 'var(--accent-purple)' },
            { step: 'Evidence Analysis', desc: 'Digital and physical evidence catalogued', icon: <FolderOpen className="w-4 h-4" />, color: 'var(--accent-teal)' },
            { step: 'AI Analytics', desc: 'Predictions, risk scores, anomaly detection', icon: <Brain className="w-4 h-4" />, color: 'var(--accent-blue)' },
            { step: 'Network Mapping', desc: 'Criminal associations and gang links identified', icon: <Network className="w-4 h-4" />, color: 'var(--accent-purple)' },
            { step: 'Reports & Closure', desc: 'Final report generated, case status updated', icon: <BarChart3 className="w-4 h-4" />, color: 'var(--accent-teal)' },
          ].map((s, i) => (
            <div key={i} className="flex items-start gap-4">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full border-2 flex items-center justify-center shrink-0" style={{ borderColor: s.color, color: s.color }}>
                  {s.icon}
                </div>
                {i < 5 && <div className="w-px h-6 bg-[var(--border-primary)]" />}
              </div>
              <div className="pb-4">
                <div className="text-sm font-semibold text-[var(--text-primary)]">{s.step}</div>
                <div className="text-xs text-[var(--text-muted)]">{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  // FAQ
  {
    id: 'faq',
    title: 'Frequently Asked Questions',
    icon: <HelpCircle className="w-4 h-4" />,
    category: 'FAQ',
    content: (
      <div className="space-y-4">
        {[
          { q: 'How do I log in to Saksha?', a: 'Use your Badge ID and PIN on the login page. Contact your administrator if you need credentials. You can also use Face ID authentication for quick access.' },
          { q: 'What browsers are supported?', a: 'Saksha supports Chrome, Firefox, Safari, and Edge (latest versions). For the best experience, use Chrome or Firefox.' },
          { q: 'How often is the data updated?', a: 'Crime data is synced in real-time from the PostgreSQL database. AI models are retrained weekly via the MLOps pipeline.' },
          { q: 'Can I export data?', a: 'Yes, most modules support CSV and PDF exports. Go to Reports Center for comprehensive report generation.' },
          { q: 'Is my data secure?', a: 'Yes. All data is encrypted in transit (HTTPS) and at rest. Authentication uses JWT tokens with role-based access control. The platform follows government security standards.' },
          { q: 'What do the AI predictions mean?', a: 'AI predictions are based on historical crime patterns and should be used as intelligence aids, not definitive conclusions. Always verify with field intelligence.' },
          { q: 'How do I report a bug or request a feature?', a: 'Contact your system administrator or use the Settings page to submit feedback. For critical issues, use the emergency contact channels.' },
        ].map((faq, i) => (
          <details key={i} className="group">
            <summary className="flex items-center gap-2 p-3 rounded-lg bg-[var(--bg-tertiary)]/50 border border-[var(--border-secondary)] cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors list-none">
              <ChevronRight className="w-4 h-4 text-[var(--text-muted)] group-open:rotate-90 transition-transform" />
              <span className="text-sm font-medium text-[var(--text-primary)]">{faq.q}</span>
            </summary>
            <div className="mt-2 ml-6 p-3 text-sm text-[var(--text-secondary)] leading-relaxed">
              {faq.a}
            </div>
          </details>
        ))}
      </div>
    ),
  },
];

const categories = ['Getting Started', 'Platform Overview', 'Module Guides', 'FAQ'];

export const DocsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [activeSection, setActiveSection] = useState('what-is-saksha');

  const filtered = search
    ? sections.filter(
        (s) =>
          s.title.toLowerCase().includes(search.toLowerCase()) ||
          s.category.toLowerCase().includes(search.toLowerCase())
      )
    : sections;

  const activeDoc = sections.find((s) => s.id === activeSection);

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-[calc(100vh-160px)]">
      {/* Left Sidebar Navigation */}
      <div className="w-full lg:w-72 shrink-0">
        <div className="sticky top-0 space-y-4">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-[var(--accent-blue)]" />
              Documentation
            </h1>
            <p className="text-sm text-[var(--text-muted)] mt-1">Learn how to use the Saksha platform</p>
          </div>

          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search docs..."
            size="sm"
          />

          <div className="space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto">
            {categories.map((cat) => {
              const catSections = filtered.filter((s) => s.category === cat);
              if (catSections.length === 0) return null;
              return (
                <div key={cat}>
                  <div className="text-[10px] font-semibold tracking-[0.1em] text-[var(--text-disabled)] uppercase mb-2 px-3">
                    {cat}
                  </div>
                  <div className="space-y-0.5">
                    {catSections.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => setActiveSection(s.id)}
                        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-left transition-colors cursor-pointer ${
                          activeSection === s.id
                            ? 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue-light)] font-medium'
                            : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        {s.icon}
                        <span className="truncate">{s.title}</span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {activeDoc && (
          <div className="sk-card-elevated sk-page-enter" key={activeDoc.id}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[var(--accent-blue-subtle)] border border-[var(--accent-blue)]/20 flex items-center justify-center text-[var(--accent-blue)]">
                {activeDoc.icon}
              </div>
              <div>
                <h2 className="text-lg font-bold text-[var(--text-primary)]">{activeDoc.title}</h2>
                <div className="flex items-center gap-2 mt-0.5">
                  <Badge variant="blue" size="xs">{activeDoc.category}</Badge>
                </div>
              </div>
            </div>
            {activeDoc.content}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocsPage;
