import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { chatQueryStream, type ChatCitation } from '../services/api';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';
import { CitationBadge } from '../components/chat/CitationBadge';
import {
  Send, Trash2, Copy, MessageSquare, Plus, FileText, Check,
  ShieldAlert, ArrowRight, RefreshCw, Search, Brain,
  ChevronRight, Bot, User, Clock, Shield, TrendingUp, MapPin, Database
} from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: Date;
  sources?: string[];
  citations?: ChatCitation[];
  followUpSuggestions?: string[];
}

interface ChatSession { id: string; title: string; messages: Message[]; }

const FOLLOW_UPS: Record<string, string[]> = {
  case_details: ["Show the FIR linked to this case", "Who are the suspects?", "What is the investigation progress?", "Show related cases"],
  fir_lookup: ["Show full FIR details", "Who is the complainant?", "What sections are charged?", "Show linked case details"],
  criminal_history: ["Show network connections", "What are known aliases?", "Find similar offenders", "Assess risk score"],
  crime_statistics: ["District-wise breakdown", "Category trends", "Compare previous period", "Crime hotspots"],
  hotspot_analysis: ["Predict future hotspots", "Crime trend forecast", "Compare districts", "Related anomalies"],
  predictions: ["Risk assessment details", "6-month forecast", "Compare districts", "Hotspot predictions"],
  dashboard_analytics: ["Recent anomalies", "Offender dossiers", "Active notifications", "Crime trends"],
};

const PROMPTS = [
  { text: "Show case CR-2026-MYS-001", icon: FileText, cat: "Cases", q: "Tell me about case CR-2026-MYS-001" },
  { text: "Crime statistics overview", icon: TrendingUp, cat: "Analytics", q: "Show me crime statistics and trends across Karnataka" },
  { text: "Find criminal Ramu Swamy", icon: Search, cat: "Criminal", q: "Tell me about criminal Ramu Swamy and his network" },
  { text: "Show FIR-789/MYS/2026", icon: ShieldAlert, cat: "FIR", q: "Show me FIR-789/MYS/2026 details and suspects" },
  { text: "Identify crime hotspots", icon: MapPin, cat: "Hotspots", q: "What are the current crime hotspots in Karnataka?" },
  { text: "Predict district risk", icon: Brain, cat: "Predict", q: "Risk assessment for Bengaluru Urban district?" },
];

export const AIChat: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try { const s = localStorage.getItem('saksha_chat_sessions'); if (s) return JSON.parse(s).map((x: any) => ({ ...x, messages: x.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })) })); } catch {}
    return [{ id: 'default', title: 'New Chat', messages: [] }];
  });
  const [sid, setSid] = useState(() => sessions[0]?.id || 'default');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sess = sessions.find(s => s.id === sid) || sessions[0];

  useEffect(() => { localStorage.setItem('saksha_chat_sessions', JSON.stringify(sessions)); }, [sessions]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [sess?.messages, loading]);

  const send = useCallback(async (text?: string) => {
    const msg = text || input;
    if (!msg.trim()) return;
    const um: Message = { id: `u-${Date.now()}`, sender: 'user', text: msg, timestamp: new Date() };
    setSessions(p => p.map(s => s.id !== sid ? s : { ...s, title: s.messages.length === 0 ? msg.slice(0, 28) + (msg.length > 28 ? '...' : '') : s.title, messages: [...s.messages, um] }));
    setInput(''); setLoading(true); setStatus('Understanding your query...');
    if (user) addLog(user.name, user.badgeId, 'REVIEW', `AI Copilot: ${msg.slice(0, 60)}`);
    const aid = `a-${Date.now()}`; let acc = ''; let fd: any = null;
    try {
      for await (const ch of chatQueryStream(msg)) {
        if (ch.type === 'status') setStatus(ch.content);
        else if (ch.type === 'token') { acc += ch.content; const s = acc; setSessions(p => p.map(x => x.id !== sid ? x : { ...x, messages: x.messages.map(m => m.id === aid ? { ...m, text: s } : m).concat(x.messages.some(m => m.id === aid) ? [] : [{ id: aid, sender: 'ai', text: s, timestamp: new Date() }]) })); }
        else if (ch.type === 'final') fd = ch.content;
      }
      const fu = FOLLOW_UPS[fd?.classification || 'general'] || FOLLOW_UPS.dashboard_analytics;
      setSessions(p => p.map(x => x.id !== sid ? x : { ...x, messages: x.messages.map(m => m.id === aid ? { ...m, text: fd?.answer || acc, sources: fd?.sources || [], citations: fd?.citations || [], followUpSuggestions: fu } : m) }));
    } catch (e: any) {
      setSessions(p => p.map(x => x.id !== sid ? x : { ...x, messages: [...x.messages, { id: aid, sender: 'ai', text: `## Error\n\n${e?.message || 'Unknown error'}\n\nEnsure backend is running on port 8000.`, timestamp: new Date() }] }));
    } finally { setLoading(false); setStatus(''); }
  }, [sessions, sid, input, user, addLog]);

  const retry = async (m: string) => { setSessions(p => p.map(s => s.id === sid ? { ...s, messages: s.messages.filter(x => x.sender !== 'ai') } : s)); await send(m); };
  const followUp = (s: string) => { setInput(s); setTimeout(() => send(s), 50); };
  const newChat = () => { const id = `s-${Date.now()}`; setSessions([{ id, title: `Chat ${sessions.length + 1}`, messages: [] }, ...sessions]); setSid(id); };
  const delChat = (id: string, e: React.MouseEvent) => { e.stopPropagation(); const f = sessions.filter(s => s.id !== id); if (!f.length) { setSessions([{ id: 'default', title: 'New Chat', messages: [] }]); setSid('default'); } else { setSessions(f); if (sid === id) setSid(f[0].id); } };
  const clearAll = () => { setSessions([{ id: 'default', title: 'New Chat', messages: [] }]); setSid('default'); localStorage.removeItem('saksha_chat_sessions'); };
  const copy = async (t: string, id: string) => { try { await navigator.clipboard.writeText(t); } catch {} setCopied(id); setTimeout(() => setCopied(null), 2000); };

  return (
    <div className="chat-root">
      {/* Sidebar */}
      <aside className="chat-side">
        <div className="chat-side-top">
          <button onClick={newChat} className="chat-side-new"><Plus size={16} /><span>New chat</span></button>
          <div className="chat-side-list">
            {sessions.map(s => (
              <div key={s.id} onClick={() => setSid(s.id)} className={`chat-side-item${s.id === sid ? ' active' : ''}`}>
                <MessageSquare size={15} />
                <span className="chat-side-item-text">{s.title}</span>
                <button onClick={e => delChat(s.id, e)} className="chat-side-del"><Trash2 size={14} /></button>
              </div>
            ))}
          </div>
        </div>
        <button onClick={clearAll} className="chat-side-clear"><Trash2 size={14} /><span>Clear all</span></button>
      </aside>

      {/* Main */}
      <main className="chat-main">
        <div className="chat-scroll custom-scrollbar">
          {sess.messages.length === 0 ? (
            /* Welcome */
            <div className="chat-welcome">
              <div className="chat-welcome-icon">
                <Bot size={28} />
              </div>
              <h2 className="chat-welcome-title">How can I help you today?</h2>
              <p className="chat-welcome-sub">I'm SAKSHA AI — ask me about cases, criminals, FIRs, statistics, or predictions.</p>
              <div className="chat-prompts">
                {PROMPTS.map((p, i) => {
                  const Ic = p.icon;
                  return (
                    <button key={i} onClick={() => send(p.q)} className="chat-prompt-card">
                      <Ic size={16} className="chat-prompt-icon" />
                      <div className="chat-prompt-body">
                        <span className="chat-prompt-cat">{p.cat}</span>
                        <span className="chat-prompt-text">{p.text}</span>
                      </div>
                      <ArrowRight size={14} className="chat-prompt-arrow" />
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Messages */
            <div className="chat-msgs">
              {sess.messages.map((m, mi) => {
                const u = m.sender === 'user';
                const last = !u && mi === sess.messages.length - 1;
                const lu = sess.messages.slice(0, mi).reverse().find(x => x.sender === 'user');
                return (
                  <div key={m.id} className={`chat-msg ${u ? 'msg-u' : 'msg-a'}`}>
                    <div className={`chat-avatar ${u ? 'av-u' : 'av-a'}`}>
                      {u ? <User size={16} /> : <Bot size={16} />}
                    </div>
                    <div className="chat-msg-body">
                      <span className="chat-msg-name">{u ? 'You' : 'SAKSHA AI'}</span>
                      {u ? (
                        <p className="chat-msg-user-text">{m.text}</p>
                      ) : (
                        <div className="chat-msg-ai-content">
                          <MarkdownRenderer content={m.text} />
                          {m.citations?.length ? <CitationBadge citations={m.citations} /> : m.sources?.length ? (
                            <div className="chat-sources">
                              <span className="chat-sources-hdr">Sources</span>
                              <div className="chat-sources-row">
                                {m.sources.map((s, i) => <span key={i} className="chat-source-tag"><FileText size={13} />{s}</span>)}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      )}
                      {/* Actions */}
                      {!u && (
                        <div className="chat-msg-actions">
                          <button onClick={() => copy(m.text, m.id)} className="chat-action-btn" title="Copy">
                            {copied === m.id ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                          {last && !loading && lu && (
                            <button onClick={() => retry(lu.text)} className="chat-action-btn" title="Regenerate">
                              <RefreshCw size={14} /><span>Regenerate</span>
                            </button>
                          )}
                        </div>
                      )}
                      {/* Follow-ups */}
                      {!u && last && !loading && m.followUpSuggestions?.length ? (
                        <div className="chat-followups">
                          {m.followUpSuggestions.map((s, i) => (
                            <button key={i} onClick={() => followUp(s)} className="chat-followup">{s}</button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {loading && (
            <div className="chat-msg msg-a">
              <div className="chat-avatar av-a"><Bot size={16} /></div>
              <div className="chat-msg-body">
                <span className="chat-msg-name">SAKSHA AI</span>
                <div className="chat-thinking">
                  <span className="chat-thinking-dot" /><span className="chat-thinking-dot" /><span className="chat-thinking-dot" />
                  <span className="chat-thinking-text">{status || 'Thinking...'}</span>
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div className="chat-input-wrap">
          <div className="chat-input-box">
            <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Message SAKSHA AI..." className="chat-ta" rows={1} />
            <button onClick={() => send()} disabled={loading || !input.trim()} className="chat-send"><Send size={18} /></button>
          </div>
          <p className="chat-input-note">Enter to send · Shift+Enter for newline</p>
        </div>
      </main>
    </div>
  );
};

export default AIChat;
