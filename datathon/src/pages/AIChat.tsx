import React, { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { chatQuery, chatQueryStream, type ChatQueryResponse, type ChatCitation } from '../services/api';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';
import { CitationBadge } from '../components/chat/CitationBadge';
import { 
  Send, Trash2, Copy, Paperclip, Sparkles, 
  MessageSquare, Plus, FileText, Check, ShieldAlert,
  ArrowRight, CornerDownLeft, ShieldCheck, RefreshCw,
  Search, Database, Brain, Zap, ChevronRight
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

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
}

const FOLLOW_UP_MAP: Record<string, string[]> = {
  case_details: [
    "Show me the FIR linked to this case",
    "Who are the suspects in this case?",
    "What is the investigation progress?",
    "Show related cases"
  ],
  fir_lookup: [
    "Show full FIR details",
    "Who is the complainant?",
    "What sections are charged?",
    "Show linked case details"
  ],
  criminal_history: [
    "Show criminal network connections",
    "What are their known aliases?",
    "Find similar offenders",
    "Assess criminal risk score"
  ],
  crime_statistics: [
    "Show district-wise breakdown",
    "Show category-wise trends",
    "Compare with previous period",
    "Identify crime hotspots"
  ],
  hotspot_analysis: [
    "Predict future hotspots",
    "Show crime trend forecast",
    "Compare hotspot districts",
    "Show related anomalies"
  ],
  predictions: [
    "Show risk assessment details",
    "Forecast for next 6 months",
    "Compare risk across districts",
    "Show hotspot predictions"
  ],
  dashboard_analytics: [
    "Show recent anomalies",
    "Show offender dossiers",
    "Show active notifications",
    "Crime trend analysis"
  ],
};

export const AIChat: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    const saved = localStorage.getItem('saksha_chat_sessions');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((s: any) => ({
          ...s,
          messages: s.messages.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }))
        }));
      } catch (e) {
        console.error("Failed to parse chat sessions", e);
      }
    }
    return [{ id: 'session-default', title: 'New Investigation Chat', messages: [] }];
  });

  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    return sessions[0]?.id || 'session-default';
  });

  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<{ name: string; size: string } | null>(null);
  const [streamStatus, setStreamStatus] = useState<string>('');
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  useEffect(() => {
    localStorage.setItem('saksha_chat_sessions', JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages, isLoading]);

  const handleSendMessage = async (textToSend?: string) => {
    const messageText = textToSend || inputMessage;
    if (!messageText.trim() && !attachedFile) return;

    const queryText = attachedFile 
      ? `[Attachment: ${attachedFile.name}] ${messageText}`
      : messageText;

    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      sender: 'user',
      text: queryText,
      timestamp: new Date()
    };

    const updatedSessions = sessions.map(s => {
      if (s.id === activeSessionId) {
        const newMsgs = [...s.messages, userMessage];
        const newTitle = s.messages.length === 0 
          ? (messageText.slice(0, 26) + (messageText.length > 26 ? '...' : '')) 
          : s.title;
        return { ...s, title: newTitle, messages: newMsgs };
      }
      return s;
    });

    setSessions(updatedSessions);
    setInputMessage('');
    setAttachedFile(null);
    setIsLoading(true);
    setStreamStatus('Analyzing query intent...');

    if (user) {
      addLog(user.name, user.badgeId, 'REVIEW', `Queried AI Copilot: ${messageText.slice(0, 60)}`);
    }

    const aiMessageId = `msg-${Date.now()}-ai`;
    let accumulatedAnswer = '';
    let finalData: any = null;

    try {
      for await (const chunk of chatQueryStream(queryText)) {
        if (chunk.type === 'status') {
          setStreamStatus(chunk.content);
        } else if (chunk.type === 'token') {
          accumulatedAnswer += chunk.content;
          setSessions(prev => prev.map(s => {
            if (s.id === activeSessionId) {
              const msgs = s.messages.map(m =>
                m.id === aiMessageId ? { ...m, text: accumulatedAnswer } : m
              );
              const exists = msgs.some(m => m.id === aiMessageId);
              if (!exists) {
                msgs.push({
                  id: aiMessageId,
                  sender: 'ai',
                  text: accumulatedAnswer,
                  timestamp: new Date(),
                });
              }
              return { ...s, messages: msgs };
            }
            return s;
          }));
        } else if (chunk.type === 'final') {
          finalData = chunk.content;
        }
      }

      const classification = finalData?.classification || 'general';
      const followUps = FOLLOW_UP_MAP[classification] || FOLLOW_UP_MAP['dashboard_analytics'];

      setSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          const msgs = s.messages.map(m => {
            if (m.id === aiMessageId) {
              return {
                ...m,
                text: finalData?.answer || accumulatedAnswer,
                sources: finalData?.sources || [],
                citations: finalData?.citations || [],
                followUpSuggestions: followUps,
              };
            }
            return m;
          });
          return { ...s, messages: msgs };
        }
        return s;
      }));
    } catch (err: any) {
      console.error('Chat error:', err);
      const detail = err?.message || 'Unknown error';
      const errorMessage: Message = {
        id: aiMessageId,
        sender: 'ai',
        text: `Error: Failed to obtain response from SAKSHA AI Engine.\n\nDetails: ${detail}\n\nEnsure the backend is running on port 8000 (npm run dev:backend).`,
        timestamp: new Date()
      };
      setSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          return { ...s, messages: [...s.messages, errorMessage] };
        }
        return s;
      }));
    } finally {
      setIsLoading(false);
      setStreamStatus('');
    }
  };

  const handleRetry = async (lastUserMessage: string) => {
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        return { ...s, messages: s.messages.filter(m => m.sender !== 'ai') };
      }
      return s;
    }));
    await handleSendMessage(lastUserMessage);
  };

  const handleFollowUpClick = (suggestion: string) => {
    setInputMessage(suggestion);
    inputRef.current?.focus();
    setTimeout(() => handleSendMessage(suggestion), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendMessage();
    }
  };

  const handleCreateNewChat = () => {
    const newSessionId = `session-${Date.now()}`;
    const newSession: ChatSession = {
      id: newSessionId,
      title: `Investigation Chat ${sessions.length + 1}`,
      messages: []
    };
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newSessionId);
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const filtered = sessions.filter(s => s.id !== sessionId);
    if (filtered.length === 0) {
      const reset = [{ id: 'session-default', title: 'New Investigation Chat', messages: [] }];
      setSessions(reset);
      setActiveSessionId('session-default');
    } else {
      setSessions(filtered);
      if (activeSessionId === sessionId) {
        setActiveSessionId(filtered[0].id);
      }
    }
  };

  const handleClearAllChats = () => {
    const reset = [{ id: 'session-default', title: 'New Investigation Chat', messages: [] }];
    setSessions(reset);
    setActiveSessionId('session-default');
    localStorage.removeItem('saksha_chat_sessions');
  };

  const handleCopyText = (text: string, msgId: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleAttachMockFile = () => {
    setAttachedFile({
      name: 'EVIDENCE-RECORD-FIR-789.pdf',
      size: '2.4 MB'
    });
  };

  const suggestedPrompts = [
    { text: "Show case CR-2026-BLR-9629", icon: FileText, category: "Case Lookup", query: "Tell me about case CR-2026-BLR-9629" },
    { text: "Crime statistics overview", icon: Zap, category: "Analytics", query: "Show me the current crime statistics and trends across Karnataka" },
    { text: "Find criminal Ramu Swamy", icon: Search, category: "Criminal", query: "Tell me about the criminal Ramu Swamy and his network" },
    { text: "Show FIR 2026/001", icon: ShieldAlert, category: "FIR", query: "Show me FIR 2026/001 details and linked suspects" },
    { text: "Identify crime hotspots", icon: Database, category: "Hotspots", query: "What are the current crime hotspots in Karnataka?" },
    { text: "Predict district risk", icon: Brain, category: "Predictions", query: "What is the risk assessment for Bengaluru Urban district?" },
  ];

  const getStepIcon = (status: string) => {
    if (status.includes('intent') || status.includes('Analyzing')) return <Search className="w-3 h-3" />;
    if (status.includes('Querying') || status.includes('backend')) return <Database className="w-3 h-3" />;
    if (status.includes('Generating') || status.includes('response')) return <Brain className="w-3 h-3" />;
    if (status.includes('Intent:')) return <Zap className="w-3 h-3" />;
    return <ChevronRight className="w-3 h-3" />;
  };

  return (
    <div className="h-[80vh] flex border border-border-color rounded-card bg-[var(--bg-secondary)]/45 overflow-hidden font-sans">
      
      {/* 1. CONVERSATION HISTORIES SIDEBAR */}
      <div className="w-64 border-r border-border-color flex flex-col justify-between bg-[var(--bg-secondary)]/40 select-none">
        <div className="p-4 flex flex-col gap-3.5 overflow-hidden flex-grow">
          
          <button 
            onClick={handleCreateNewChat}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-[var(--text-primary)] font-mono text-[10.5px] font-bold uppercase rounded-btn transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Investigation</span>
          </button>

          <div className="flex-grow overflow-y-auto flex flex-col gap-1.5 custom-scrollbar pr-1">
            <span className="text-[8px] font-mono text-[var(--text-muted)] uppercase tracking-widest block mb-1">
              Active Briefing Files
            </span>
            {sessions.map(s => {
              const isActive = s.id === activeSessionId;
              const msgCount = s.messages.length;
              return (
                <div 
                  key={s.id}
                  onClick={() => setActiveSessionId(s.id)}
                  className={`flex items-center justify-between p-2.5 rounded border transition-all cursor-pointer font-mono text-[10px] ${
                    isActive 
                      ? 'bg-[#1E6FD9]/10 border-[#1E6FD9]/30 text-[var(--text-primary)] font-bold'
                      : 'bg-transparent border-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/10'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                    <div className="flex flex-col truncate">
                      <span className="truncate">{s.title}</span>
                      <span className="text-[8px] text-[var(--text-secondary)]">{msgCount} message{msgCount !== 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  <button 
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="p-1 text-[var(--text-secondary)] hover:text-red-400 rounded transition-colors shrink-0"
                    title="Delete Chat"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        <div className="p-3 border-t border-border-color flex justify-center bg-[var(--bg-secondary)]/20">
          <button 
            onClick={handleClearAllChats}
            className="flex items-center gap-1 text-[9px] font-mono text-red-400 hover:text-red-500 transition-colors uppercase font-bold cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Archive</span>
          </button>
        </div>
      </div>

      {/* 2. MAIN CHAT WORKSPACE */}
      <div className="flex-1 flex flex-col justify-between bg-transparent overflow-hidden">
        
        <div className="flex-grow overflow-y-auto p-5 space-y-5 custom-scrollbar">
          {activeSession.messages.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center max-w-2xl mx-auto space-y-6 select-none pt-8">
              
              <div className="w-16 h-16 rounded-2xl bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 flex items-center justify-center text-[#1E6FD9] shadow-glow-blue animate-pulse">
                <Sparkles className="w-9 h-9" />
              </div>
              
              <div className="text-center">
                <h3 className="text-[17px] font-extrabold uppercase tracking-wider text-[var(--text-primary)]">
                  SAKSHA Copilot AI
                </h3>
                <p className="text-[11px] font-mono text-[var(--text-muted)] mt-1.5 uppercase tracking-widest">
                  Secure Law Enforcement Intelligence Assistant
                </p>
                <p className="text-[9px] font-mono text-[var(--text-secondary)] mt-3 max-w-md leading-relaxed">
                  Ask about cases, criminals, FIRs, crime statistics, hotspots, predictions, or network analysis. 
                  Data is sourced directly from the Saksha database.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 w-full mt-4">
                {suggestedPrompts.map((p, idx) => {
                  const Icon = p.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(p.query)}
                      disabled={isLoading}
                      className="p-3 bg-[var(--bg-secondary)]/40 border border-[var(--border-primary)] rounded-card text-left text-[10px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[#1E6FD9]/45 hover:bg-[var(--bg-tertiary)]/20 transition-all flex flex-col justify-between group cursor-pointer h-24 disabled:opacity-50"
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <Icon className="w-3.5 h-3.5 text-[#1E6FD9]" />
                        <span className="text-[8px] text-[var(--text-muted)] uppercase font-bold">{p.category}</span>
                      </div>
                      <span className="font-bold text-[var(--text-primary)] text-[11px]">{p.text}</span>
                      <span className="flex items-center justify-between w-full text-[9px] text-[var(--text-secondary)] font-mono mt-auto">
                        Run query
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {activeSession.messages.map((msg, msgIdx) => {
                const isUser = msg.sender === 'user';
                const isLastAIMessage = !isUser && msgIdx === activeSession.messages.length - 1;
                const lastUserMsg = activeSession.messages.slice(0, msgIdx).reverse().find(m => m.sender === 'user');
                
                return (
                  <div 
                    key={msg.id}
                    className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <div className="flex items-center gap-2 font-mono text-[9px] text-[var(--text-muted)] select-none">
                      <span>{isUser ? 'INVESTIGATOR' : 'SAKSHA CORE AI'}</span>
                      <span>·</span>
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>

                    <div className={`p-4 rounded-card border text-[11.5px] leading-relaxed max-w-[85%] text-left font-mono ${
                      isUser
                        ? 'bg-[#1E6FD9]/10 border-[#1E6FD9]/20 text-[var(--text-primary)]'
                        : 'bg-[var(--bg-tertiary)]/35 border-[var(--border-primary)] text-[var(--text-secondary)] shadow-md relative group'
                    }`}>
                      
                      {isUser ? (
                        <div className="whitespace-pre-wrap">{msg.text}</div>
                      ) : (
                        <MarkdownRenderer content={msg.text} />
                      )}

                      {!isUser && msg.citations && msg.citations.length > 0 ? (
                        <CitationBadge citations={msg.citations} />
                      ) : (
                        msg.sources && msg.sources.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-[var(--border-primary)] select-none">
                            <span className="text-[8.5px] font-bold text-[#0E9E78] uppercase tracking-widest block mb-2">
                              Intelligence References (Sources)
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {msg.sources.map((src, sIdx) => (
                                <div 
                                  key={sIdx}
                                  className="px-2.5 py-1 bg-[var(--bg-secondary)]/60 border border-[var(--border-primary)] rounded text-[8px] text-[var(--text-secondary)] flex items-center gap-1 font-mono hover:border-[var(--border-primary)] transition-colors"
                                >
                                  <FileText className="w-3 h-3 text-[#0E9E78]" />
                                  <span>{src}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      )}

                      {!isUser && (
                        <button
                          onClick={() => handleCopyText(msg.text, msg.id)}
                          className="absolute right-3 top-3 p-1 bg-[var(--bg-secondary)]/70 border border-[var(--border-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                          title="Copy AI Response"
                        >
                          {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>

                    {!isUser && isLastAIMessage && !isLoading && (
                      <div className="flex items-center gap-2 mt-1 ml-1">
                        {lastUserMsg && (
                          <button
                            onClick={() => handleRetry(lastUserMsg.text)}
                            className="flex items-center gap-1.5 px-2.5 py-1 bg-[var(--bg-secondary)]/50 border border-[var(--border-primary)] rounded text-[9px] font-mono text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-secondary)] transition-all cursor-pointer"
                            title="Regenerate response"
                          >
                            <RefreshCw className="w-3 h-3" />
                            <span>Regenerate</span>
                          </button>
                        )}
                      </div>
                    )}

                    {!isUser && msg.followUpSuggestions && msg.followUpSuggestions.length > 0 && isLastAIMessage && !isLoading && (
                      <div className="flex flex-wrap gap-2 mt-2 ml-1 max-w-[85%]">
                        <span className="text-[8px] font-mono text-[var(--text-secondary)] uppercase self-center mr-1">Follow up:</span>
                        {msg.followUpSuggestions.map((suggestion, sIdx) => (
                          <button
                            key={sIdx}
                            onClick={() => handleFollowUpClick(suggestion)}
                            disabled={isLoading}
                            className="px-3 py-1.5 bg-[#1E6FD9]/10 border border-[#1E6FD9]/25 rounded-btn text-[9.5px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[#1E6FD9]/50 hover:bg-[#1E6FD9]/15 transition-all cursor-pointer disabled:opacity-50"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col gap-1.5 items-start max-w-4xl mx-auto">
              <div className="font-mono text-[9px] text-[var(--text-muted)] uppercase">
                SAKSHA CORE AI
              </div>
              <div className="p-4 bg-[var(--bg-tertiary)]/35 border border-[var(--border-primary)] rounded-card">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-[var(--text-muted)]">
                    {getStepIcon(streamStatus)}
                    <span className="uppercase tracking-widest">
                      {streamStatus || 'Querying backend services...'}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3 mt-2">
                  {['Analyzing', 'Querying', 'Generating'].map((step, idx) => {
                    const isDone = streamStatus.includes('Generating') || 
                                   (streamStatus.includes('Retrieved') && idx < 2) ||
                                   (streamStatus.includes('Intent') && idx === 0);
                    const isCurrent = (idx === 0 && streamStatus.includes('Analyzing')) ||
                                     (idx === 1 && (streamStatus.includes('Querying') || streamStatus.includes('Intent') || streamStatus.includes('Retrieved'))) ||
                                     (idx === 2 && streamStatus.includes('Generating'));
                    return (
                      <div key={step} className={`flex items-center gap-1 text-[8px] font-mono uppercase ${
                        isCurrent ? 'text-[#1E6FD9]' : isDone ? 'text-[#0E9E78]' : 'text-[var(--text-disabled)]'
                      }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${
                          isCurrent ? 'bg-[#1E6FD9] animate-pulse' : isDone ? 'bg-[#0E9E78]' : 'bg-[var(--bg-elevated)]'
                        }`} />
                        <span>{step}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-border-color bg-[var(--bg-secondary)]/20">
          <div className="max-w-4xl mx-auto flex flex-col gap-2 relative">
            
            {attachedFile && (
              <div className="self-start flex items-center gap-1.5 px-2 py-0.5 bg-[#0E9E78]/15 border border-[#0E9E78]/40 text-[#0E9E78] text-[9.5px] font-mono rounded">
                <Paperclip className="w-3 h-3" />
                <span>{attachedFile.name} ({attachedFile.size})</span>
                <button 
                  onClick={() => setAttachedFile(null)} 
                  className="text-red-400 font-bold ml-1 hover:text-red-500 transition-colors"
                >
                  x
                </button>
              </div>
            )}

            <div className="flex items-end gap-2.5 bg-[var(--bg-secondary)]/70 border border-[var(--border-primary)] focus-within:border-[#1E6FD9]/45 rounded-card p-2">
              
              <button
                onClick={handleAttachMockFile}
                className="p-2 text-[var(--text-muted)] hover:text-[#0E9E78] rounded transition-colors shrink-0 cursor-pointer"
                title="Attach Evidence Document"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask SAKSHA AI to analyze crime files, query offender connections..."
                className="flex-grow bg-transparent outline-none border-none text-[var(--text-primary)] text-[11px] font-mono resize-none max-h-24 py-1.5 placeholder-slate-600 custom-scrollbar"
                rows={1}
              />

              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading}
                className="p-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-[var(--text-primary)] disabled:opacity-30 rounded-btn shrink-0 flex items-center justify-center transition-colors cursor-pointer"
                title="Send Message"
              >
                <Send className="w-4.5 h-4.5" />
              </button>
            </div>
            <div className="flex justify-between items-center text-[7.5px] text-[var(--text-secondary)] uppercase select-none px-1">
              <span>Press Enter to send, Shift+Enter for newline</span>
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-[#0E9E78]" />
                End-to-End Cryptographic Tunnel Encrypted
              </span>
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
};

export default AIChat;
