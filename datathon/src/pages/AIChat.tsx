import React, { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { chatQuery, type ChatQueryResponse, type ChatCitation } from '../services/api';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';
import { CitationBadge } from '../components/chat/CitationBadge';
import { 
  Send, Trash2, Copy, Paperclip, Sparkles, 
  MessageSquare, Plus, FileText, Check, ShieldAlert,
  ArrowRight, CornerDownLeft, ShieldCheck
} from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: Date;
  sources?: string[];
  citations?: ChatCitation[];
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
}

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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  // Save sessions to localStorage
  useEffect(() => {
    localStorage.setItem('saksha_chat_sessions', JSON.stringify(sessions));
  }, [sessions]);

  // Scroll to bottom
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

    // Update active session messages
    const updatedSessions = sessions.map(s => {
      if (s.id === activeSessionId) {
        const newMsgs = [...s.messages, userMessage];
        // Auto update title if it's the first message
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

    // Log the audit event
    if (user) {
      addLog(user.name, user.badgeId, 'REVIEW', `Queried AI Copilot: ${messageText.slice(0, 60)}`);
    }

    try {
      // Call actual backend chatQuery API
      const result: ChatQueryResponse = await chatQuery(messageText);

      const aiMessage: Message = {
        id: `msg-${Date.now()}-ai`,
        sender: 'ai',
        text: result.answer,
        timestamp: new Date(),
        sources: result.sources || [],
        citations: result.citations || []
      };

      setSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          return { ...s, messages: [...s.messages, aiMessage] };
        }
        return s;
      }));
    } catch (err) {
      const errorMessage: Message = {
        id: `msg-${Date.now()}-ai`,
        sender: 'ai',
        text: "Error: Failed to obtain response from SAKSHA AI Engine. Please check backend service connectivity.",
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
    }
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
    // Simulate attaching evidence document
    setAttachedFile({
      name: 'EVIDENCE-RECORD-FIR-789.pdf',
      size: '2.4 MB'
    });
  };

  const suggestedPrompts = [
    { text: "Analyze cybercrime trends in Bengaluru Urban", query: "Can you analyze recent cybercrime trends in Bengaluru Urban and identify the key hotspot sectors?" },
    { text: "Find open cases for Whitefield Station", query: "List all open crime cases currently registered under Whitefield Police Station." },
    { text: "Identify key suspect network nodes", query: "Can you show me the primary suspect nodes and their connections for Devaraja Police Limit?" },
    { text: "Summarize anomalies and alerts", query: "Explain the active security anomalies and threat scores detected in the last audit cycle." }
  ];

  return (
    <div className="h-[80vh] flex border border-border-color rounded-card bg-[#0a1220]/45 overflow-hidden font-sans">
      
      {/* 1. CONVERSATION HISTORIES SIDEBAR */}
      <div className="w-64 border-r border-border-color flex flex-col justify-between bg-slate-950/40 select-none">
        <div className="p-4 flex flex-col gap-3.5 overflow-hidden flex-grow">
          
          {/* New Chat Button */}
          <button 
            onClick={handleCreateNewChat}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-white font-mono text-[10.5px] font-bold uppercase rounded-btn transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Investigation</span>
          </button>

          {/* Session List */}
          <div className="flex-grow overflow-y-auto flex flex-col gap-1.5 custom-scrollbar pr-1">
            <span className="text-[8px] font-mono text-slate-500 uppercase tracking-widest block mb-1">
              Active Briefing Files
            </span>
            {sessions.map(s => {
              const isActive = s.id === activeSessionId;
              return (
                <div 
                  key={s.id}
                  onClick={() => setActiveSessionId(s.id)}
                  className={`flex items-center justify-between p-2.5 rounded border transition-all cursor-pointer font-mono text-[10px] ${
                    isActive 
                      ? 'bg-[#1E6FD9]/10 border-[#1E6FD9]/30 text-white font-bold'
                      : 'bg-transparent border-transparent text-[#A8B4CC] hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{s.title}</span>
                  </div>
                  <button 
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="p-1 text-slate-600 hover:text-red-400 rounded transition-colors shrink-0"
                    title="Delete Chat"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Clear All Bottom bar */}
        <div className="p-3 border-t border-border-color flex justify-center bg-slate-950/20">
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
        
        {/* Chat Feed viewport */}
        <div className="flex-grow overflow-y-auto p-5 space-y-5 custom-scrollbar">
          {activeSession.messages.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center max-w-2xl mx-auto space-y-6 select-none pt-8">
              
              {/* Logo / Copilot Emblem */}
              <div className="w-16 h-16 rounded-2xl bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 flex items-center justify-center text-[#1E6FD9] shadow-glow-blue animate-pulse">
                <Sparkles className="w-9 h-9" />
              </div>
              
              <div className="text-center">
                <h3 className="text-[17px] font-extrabold uppercase tracking-wider text-white">
                  SAKSHA Copilot AI
                </h3>
                <p className="text-[11px] font-mono text-[#6A7A96] mt-1.5 uppercase tracking-widest">
                  Secure Law Enforcement Intelligence Assistant
                </p>
              </div>

              {/* Grid of Suggested Prompts */}
              <div className="grid grid-cols-2 gap-3.5 w-full mt-4">
                {suggestedPrompts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputMessage(p.query);
                      inputRef.current?.focus();
                    }}
                    className="p-3.5 bg-slate-950/40 border border-slate-900 rounded-card text-left text-[11px] text-[#A8B4CC] hover:text-white hover:border-[#1E6FD9]/45 hover:bg-slate-900/20 transition-all flex flex-col justify-between group cursor-pointer h-24"
                  >
                    <span className="font-bold text-white mb-2">{p.text}</span>
                    <span className="flex items-center justify-between w-full text-[9.5px] text-slate-500 font-mono">
                      Query template
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:translate-x-1 transition-transform" />
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {activeSession.messages.map((msg) => {
                const isUser = msg.sender === 'user';
                return (
                  <div 
                    key={msg.id}
                    className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <div className="flex items-center gap-2 font-mono text-[9px] text-slate-500 select-none">
                      <span>{isUser ? 'INVESTIGATOR' : 'SAKSHA CORE AI'}</span>
                      <span>•</span>
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>

                    <div className={`p-4 rounded-card border text-[11.5px] leading-relaxed max-w-[85%] text-left font-mono ${
                      isUser
                        ? 'bg-[#1E6FD9]/10 border-[#1E6FD9]/20 text-white'
                        : 'bg-[#111D35]/35 border-slate-900 text-[#A8B4CC] shadow-md relative group'
                    }`}>
                      
                      {/* Text details / Markdown-like layout */}
                      {isUser ? (
                        <div className="whitespace-pre-wrap">{msg.text}</div>
                      ) : (
                        <MarkdownRenderer content={msg.text} />
                      )}

                      {/* AI Response References / Source Cards */}
                      {!isUser && msg.citations && msg.citations.length > 0 ? (
                        <CitationBadge citations={msg.citations} />
                      ) : (
                        msg.sources && msg.sources.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-slate-900 select-none">
                            <span className="text-[8.5px] font-bold text-[#0E9E78] uppercase tracking-widest block mb-2">
                              Intelligence References (Sources)
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {msg.sources.map((src, sIdx) => (
                                <div 
                                  key={sIdx}
                                  className="px-2.5 py-1 bg-slate-950/60 border border-slate-900 rounded text-[8px] text-[#A8B4CC] flex items-center gap-1 font-mono hover:border-slate-800 transition-colors"
                                >
                                  <FileText className="w-3 h-3 text-[#0E9E78]" />
                                  <span>{src}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      )}

                      {/* Action buttons (Only for AI bubble) */}
                      {!isUser && (
                        <button
                          onClick={() => handleCopyText(msg.text, msg.id)}
                          className="absolute right-3 top-3 p-1 bg-slate-950/70 border border-slate-900 text-slate-400 hover:text-white rounded opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                          title="Copy AI Response"
                        >
                          {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Streaming loader */}
          {isLoading && (
            <div className="flex flex-col gap-1.5 items-start max-w-4xl mx-auto">
              <div className="font-mono text-[9px] text-slate-500 uppercase">
                SAKSHA CORE AI • Querying Models
              </div>
              <div className="p-4 bg-[#111D35]/35 border border-slate-900 rounded-card flex items-center gap-3">
                <div className="flex space-x-1.5">
                  <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-[#1E6FD9] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  Scanning crime records...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Chat input bar */}
        <div className="p-4 border-t border-border-color bg-slate-950/20">
          <div className="max-w-4xl mx-auto flex flex-col gap-2 relative">
            
            {/* Attachment Badge */}
            {attachedFile && (
              <div className="self-start flex items-center gap-1.5 px-2 py-0.5 bg-[#0E9E78]/15 border border-[#0E9E78]/40 text-[#0E9E78] text-[9.5px] font-mono rounded">
                <Paperclip className="w-3 h-3" />
                <span>{attachedFile.name} ({attachedFile.size})</span>
                <button 
                  onClick={() => setAttachedFile(null)} 
                  className="text-red-400 font-bold ml-1 hover:text-red-500 transition-colors"
                >
                  ×
                </button>
              </div>
            )}

            <div className="flex items-end gap-2.5 bg-slate-950/70 border border-slate-900 focus-within:border-[#1E6FD9]/45 rounded-card p-2">
              
              {/* Attach File Button */}
              <button
                onClick={handleAttachMockFile}
                className="p-2 text-slate-500 hover:text-[#0E9E78] rounded transition-colors shrink-0 cursor-pointer"
                title="Attach Evidence Document"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              {/* Text Input area */}
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask SAKSHA AI to analyze crime files, query offender connections..."
                className="flex-grow bg-transparent outline-none border-none text-white text-[11px] font-mono resize-none max-h-24 py-1.5 placeholder-slate-600 custom-scrollbar"
                rows={1}
              />

              {/* Send Button */}
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading}
                className="p-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-white disabled:opacity-30 rounded-btn shrink-0 flex items-center justify-center transition-colors cursor-pointer"
                title="Send Message"
              >
                <Send className="w-4.5 h-4.5" />
              </button>
            </div>
            <div className="flex justify-between items-center text-[7.5px] text-slate-600 uppercase select-none px-1">
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
