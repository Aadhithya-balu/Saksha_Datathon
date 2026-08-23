import React from 'react';
import {
  AlertTriangle, Info, CheckCircle, XCircle, FileText
} from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

type Block =
  | { type: 'h1'; text: string }
  | { type: 'h2'; text: string }
  | { type: 'h3'; text: string }
  | { type: 'code'; lang: string; lines: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'callout'; variant: 'info'|'warning'|'success'|'danger'|'note'; text: string }
  | { type: 'quote'; text: string }
  | { type: 'hr' }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'p'; text: string }
  | { type: 'br' };

function parse(src: string): Block[] {
  const lines = src.split('\n');
  const out: Block[] = [];
  let i = 0;
  const peek = () => lines[i]?.trim() ?? '';

  while (i < lines.length) {
    const t = peek();
    if (!t) { i++; out.push({ type: 'br' }); continue; }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(t)) { i++; out.push({ type: 'hr' }); continue; }
    if (t.startsWith('```')) {
      const lang = t.slice(3).trim();
      const cl: string[] = []; i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) { cl.push(lines[i]); i++; }
      i++; out.push({ type: 'code', lang, lines: cl }); continue;
    }
    const hm = t.match(/^#{1,3}\s+(.*)/);
    if (hm) {
      const lvl = t.split(' ')[0].length;
      out.push({ type: lvl === 1 ? 'h1' : lvl === 2 ? 'h2' : 'h3', text: hm[1] });
      i++; continue;
    }
    const cm = t.match(/^\[!(info|warning|success|danger|note)\]\s*(.*)/i);
    if (cm) {
      const vl = cm[1].toLowerCase() as Block['type'] extends { variant: infer V } ? V : never;
      const buf = [cm[2] || '']; i++;
      while (i < lines.length && lines[i].trim() && !lines[i].trim().startsWith('#') && !lines[i].trim().startsWith('[') && !lines[i].trim().startsWith('```')) { buf.push(lines[i].trim()); i++; }
      out.push({ type: 'callout', variant: vl as any, text: buf.join(' ') }); continue;
    }
    if (t.includes('|') && i + 1 < lines.length && lines[i + 1]?.trim().match(/^\|[\s\-:|]+\|$/)) {
      const pr = (r: string) => r.split('|').map(c => c.trim()).filter((_, j, a) => j > 0 && j < a.length - 1);
      const hdrs = pr(t); i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes('|')) { rows.push(pr(lines[i].trim())); i++; }
      out.push({ type: 'table', headers: hdrs, rows }); continue;
    }
    if (t.startsWith('> ')) {
      const buf = [t.slice(2)]; i++;
      while (i < lines.length && lines[i].trim().startsWith('> ')) { buf.push(lines[i].trim().slice(2)); i++; }
      out.push({ type: 'quote', text: buf.join(' ') }); continue;
    }
    if (t.startsWith('- ') || t.startsWith('* ')) {
      const items: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) { items.push(lines[i].trim().slice(2)); i++; }
      out.push({ type: 'ul', items }); continue;
    }
    const nm = t.match(/^(\d+)\.\s+(.*)/);
    if (nm) {
      const items: string[] = [];
      while (i < lines.length && lines[i].trim().match(/^\d+\.\s+/)) { items.push(lines[i].trim().replace(/^\d+\.\s+/, '')); i++; }
      out.push({ type: 'ol', items }); continue;
    }
    const buf = [t]; i++;
    while (i < lines.length && lines[i].trim() && !lines[i].trim().startsWith('#') && !lines[i].trim().startsWith('```') && !lines[i].trim().startsWith('> ') && !lines[i].trim().startsWith('- ') && !lines[i].trim().startsWith('* ') && !lines[i].trim().match(/^\d+\.\s+/) && !lines[i].trim().startsWith('[!') && !lines[i].trim().match(/^\|/) && !lines[i].trim().match(/^(-{3,}|\*{3,}|_{3,})$/)) { buf.push(lines[i].trim()); i++; }
    out.push({ type: 'p', text: buf.join(' ') });
  }
  return out;
}

function fmt(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let rem = text; let k = 0;
  const pushPlain = (t: string) => { if (t) parts.push(t); };
  while (rem.length > 0) {
    // "Label: value" field labels render bold — README-preview look without markdown.
    const f = rem.match(/(^|[\s|])([A-Z][A-Za-z0-9/&()'.\- ]{1,28}):\s/);
    const b = rem.match(/^(.*?)\*\*(.*?)\*\*(.*)/);
    const eq = rem.match(/(^|[,\s])([A-Z][A-Za-z]{2,20})=/);
    if (f && (!b || (f.index ?? 0) <= (b.index ?? Infinity)) && (!eq || (f.index ?? 0) <= (eq.index ?? Infinity))) {
      pushPlain(rem.slice(0, f.index));
      parts.push(
        <span key={k++} className="chat-md-field">
          <strong>{f[2]}:</strong>{" "}
        </span>
      );
      rem = rem.slice((f.index ?? 0) + f[0].length);
      continue;
    }
    if (b && (!c_match(rem) || b.index! <= c_match(rem)!)) {
      if (b[1]) parts.push(b[1]);
      parts.push(<strong key={k++} style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{b[2]}</strong>);
      rem = b[3];
    } else if (c_match(rem) !== null && c_match(rem) !== undefined) {
      const c = rem.match(/^(.*?)`(.*?)`(.*)/)!;
      if (c[1]) parts.push(c[1]);
      parts.push(<code key={k++} className="chat-md-code">{c[2]}</code>);
      rem = c[3];
    } else if (eq) {
      pushPlain(rem.slice(0, eq.index));
      parts.push(<span key={k++} className="chat-md-eqkey"><strong>{eq[2]}</strong>=</span>);
      rem = rem.slice((eq.index ?? 0) + eq[0].length);
    } else { parts.push(rem); break; }
  }
  return <>{parts}</>;
}

function c_match(text: string): number | null {
  const m = text.match(/`/);
  return m ? m.index ?? null : null;
}

/** Renders a record item as stacked "Field: value" rows (README-preview card). */
function renderRecord(item: string): React.ReactNode {
  if (!item.includes(' | ')) return fmt(item);
  const fields = item.split(' | ').map(s => s.trim()).filter(Boolean);
  return (
    <span className="chat-md-record">
      {fields.map((field, i) => (
        <span key={i} className="chat-md-record-row">{fmt(field)}</span>
      ))}
    </span>
  );
}

const CALLOUT: Record<string, { icon: React.ElementType; cls: string; label: string }> = {
  info:    { icon: Info,          cls: 'co-info',    label: 'Info' },
  warning: { icon: AlertTriangle, cls: 'co-warn',    label: 'Warning' },
  success: { icon: CheckCircle,   cls: 'co-ok',      label: 'Success' },
  danger:  { icon: XCircle,       cls: 'co-danger',  label: 'Critical' },
  note:    { icon: FileText,      cls: 'co-note',    label: 'Note' },
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;
  const blocks = parse(content);
  const els: React.ReactNode[] = [];

  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i]; const k = i;
    switch (b.type) {
      case 'br': els.push(<div key={k} style={{ height: 8 }} />); break;
      case 'hr': els.push(<hr key={k} className="chat-md-hr" />); break;
      case 'h1': els.push(<h2 key={k} className="chat-md-h1">{fmt(b.text)}</h2>); break;
      case 'h2': els.push(<h3 key={k} className="chat-md-h2">{fmt(b.text)}</h3>); break;
      case 'h3': els.push(<h4 key={k} className="chat-md-h3">{fmt(b.text)}</h4>); break;
      case 'p':
        els.push(
          /^Source: Saksha Database/.test(b.text)
            ? <p key={k} className="chat-md-footer">{b.text}</p>
            : <p key={k} className="chat-md-p">{fmt(b.text)}</p>
        ); break;
      case 'quote': els.push(<blockquote key={k} className="chat-md-quote">{fmt(b.text)}</blockquote>); break;
      case 'ul': els.push(<ul key={k} className="chat-md-ul">{b.items.map((it, j) => <li key={j}>{renderRecord(it)}</li>)}</ul>); break;
      case 'ol': els.push(<ol key={k} className="chat-md-ol">{b.items.map((it, j) => <li key={j}>{renderRecord(it)}</li>)}</ol>); break;
      case 'code':
        els.push(
          <div key={k} className="chat-md-codeblock">
            {b.lang && <div className="chat-md-codelang">{b.lang}</div>}
            <pre><code>{b.lines.join('\n')}</code></pre>
          </div>
        ); break;
      case 'table':
        els.push(
          <div key={k} className="chat-md-tablewrap">
            <table className="chat-md-table">
              <thead><tr>{b.headers.map((h, j) => <th key={j}>{fmt(h)}</th>)}</tr></thead>
              <tbody>{b.rows.map((r, ri) => <tr key={ri}>{r.map((c, ci) => <td key={ci}>{fmt(c)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        ); break;
      case 'callout': {
        const cfg = CALLOUT[b.variant] || CALLOUT.note;
        const Ic = cfg.icon;
        els.push(
          <div key={k} className={`chat-md-callout ${cfg.cls}`}>
            <Ic className="chat-md-callout-ic" />
            <div><div className="chat-md-callout-lbl">{cfg.label}</div><div>{fmt(b.text)}</div></div>
          </div>
        ); break;
      }
    }
  }
  return <div className={`chat-md ${className}`}>{els}</div>;
};

export default MarkdownRenderer;
