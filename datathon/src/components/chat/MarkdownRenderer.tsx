import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split lines into blocks
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockBuffer: string[] = [];
  let codeLanguage = '';

  lines.forEach((line, index) => {
    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // End code block
        elements.push(
          <div key={`code-${index}`} className="my-2 p-3 bg-slate-950 border border-slate-800 rounded text-xs font-mono overflow-x-auto text-emerald-400">
            {codeLanguage && <div className="text-[9px] font-bold uppercase text-slate-500 mb-1">{codeLanguage}</div>}
            <pre className="whitespace-pre">{codeBlockBuffer.join('\n')}</pre>
          </div>
        );
        codeBlockBuffer = [];
        inCodeBlock = false;
      } else {
        // Start code block
        inCodeBlock = true;
        codeLanguage = line.trim().slice(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockBuffer.push(line);
      return;
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={index} className="text-xs font-bold text-white uppercase tracking-wider mt-3 mb-1 font-mono">
          {formatInline(line.slice(4))}
        </h4>
      );
      return;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h3 key={index} className="text-sm font-extrabold text-white uppercase tracking-wider mt-3 mb-1.5 font-mono">
          {formatInline(line.slice(3))}
        </h3>
      );
      return;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h2 key={index} className="text-base font-black text-white uppercase tracking-widest mt-4 mb-2 font-mono border-b border-slate-800 pb-1">
          {formatInline(line.slice(2))}
        </h2>
      );
      return;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={index} className="my-1.5 pl-3 border-l-2 border-[#1E6FD9] text-slate-300 italic text-[11px]">
          {formatInline(line.slice(2))}
        </blockquote>
      );
      return;
    }

    // Bullet lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const itemText = line.trim().slice(2);
      elements.push(
        <div key={index} className="flex items-start gap-2 my-0.5 pl-2 text-[11.5px] leading-relaxed">
          <span className="text-[#1E6FD9] font-bold shrink-0">•</span>
          <span>{formatInline(itemText)}</span>
        </div>
      );
      return;
    }

    // Numbered lists
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div key={index} className="flex items-start gap-2 my-0.5 pl-2 text-[11.5px] leading-relaxed">
          <span className="text-[#0E9E78] font-mono text-[10px] font-bold shrink-0">{numMatch[1]}.</span>
          <span>{formatInline(numMatch[2])}</span>
        </div>
      );
      return;
    }

    // Empty lines
    if (!line.trim()) {
      elements.push(<div key={index} className="h-2" />);
      return;
    }

    // Regular paragraph line
    elements.push(
      <p key={index} className="my-1 text-[11.5px] leading-relaxed">
        {formatInline(line)}
      </p>
    );
  });

  return <div className={`markdown-content font-mono ${className}`}>{elements}</div>;
};

// Simple inline formatting helper for bold, italic, and code snippets
function formatInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    // Bold **text**
    const boldMatch = remaining.match(/^(.*?)\*\*(.*?)\*\*(.*)/);
    // Inline code `code`
    const codeMatch = remaining.match(/^(.*?)`(.*?)`(.*)/);

    if (boldMatch && (!codeMatch || boldMatch.index! <= codeMatch.index!)) {
      if (boldMatch[1]) parts.push(boldMatch[1]);
      parts.push(
        <strong key={`b-${keyIdx++}`} className="font-bold text-white">
          {boldMatch[2]}
        </strong>
      );
      remaining = boldMatch[3];
    } else if (codeMatch) {
      if (codeMatch[1]) parts.push(codeMatch[1]);
      parts.push(
        <code key={`c-${keyIdx++}`} className="px-1.5 py-0.5 bg-slate-950 border border-slate-800 rounded text-[10.5px] font-mono text-[#0E9E78]">
          {codeMatch[2]}
        </code>
      );
      remaining = codeMatch[3];
    } else {
      parts.push(remaining);
      break;
    }
  }

  return <>{parts}</>;
}

export default MarkdownRenderer;
