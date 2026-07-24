import React, { useState } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { investigationChat } from '../../services/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  caseId: string;
}

const AIChatPanel: React.FC<Props> = ({ caseId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Ask me anything about this investigation case. I can help analyze evidence, suggest leads, or summarize case details.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await investigationChat(caseId, userMessage.content);
      setMessages(prev => [...prev, { role: 'assistant', content: response.answer || 'No response generated.' }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message || 'Failed to get response'}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card flex flex-col h-full min-h-[300px]">
      {/* Header */}
      <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3 shrink-0">
        <Bot className="w-4 h-4 text-[var(--accent-teal)]" /> AI Investigation Assistant
        <Sparkles className="w-3 h-3 text-[var(--accent-teal)] animate-pulse ml-auto" />
      </h3>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3 mb-3 min-h-0 pr-1">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-6 h-6 rounded bg-[var(--accent-teal)]/10 border border-[var(--accent-teal)]/30 flex items-center justify-center text-[var(--accent-teal)] shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}
            <div className={`max-w-[85%] p-2.5 rounded text-[10px] leading-relaxed ${
              msg.role === 'user'
                ? 'bg-[var(--accent-blue)]/15 border border-[var(--accent-blue)]/20 text-[var(--text-primary)]'
                : 'bg-[var(--bg-secondary)]/50 border border-[var(--border-primary)] text-[var(--text-secondary)]'
            }`}>
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-6 h-6 rounded bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/30 flex items-center justify-center text-[var(--accent-blue)] shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-[var(--text-muted)] text-[9px] uppercase">
            <div className="w-3 h-3 rounded-full border border-[var(--accent-teal)] border-t-transparent animate-spin" />
            Analyzing case data...
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this investigation..."
          className="flex-1 px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded text-[10px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent-teal)]/60 focus:outline-none uppercase"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-3 py-2 bg-[var(--accent-teal)] hover:bg-[var(--accent-teal)]/80 disabled:opacity-50 text-[var(--text-primary)] rounded transition-colors cursor-pointer shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};

export default AIChatPanel;

