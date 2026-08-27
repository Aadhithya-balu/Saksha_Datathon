import React, { useState } from 'react';
import { KeyRound, X, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { changePassword } from '../../services/api';
import { useAuthStore } from '../../store/authStore';

interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}

type Feedback = { kind: 'success' | 'error'; text: string } | null;

export const ChangePasswordModal: React.FC<ChangePasswordModalProps> = ({ open, onClose }) => {
  const badgeId = useAuthStore((s) => s.user?.badgeId);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  if (!open) return null;

  const toggleShow = (key: string) => setShow((s) => ({ ...s, [key]: !s[key] }));

  const isSixDigitPin = (v: string) => v.length === 6 && /^\d{6}$/.test(v);

  const validate = (): string | null => {
    if (!current) return 'Enter your current password.';
    if (!next) return 'Enter a new password.';
    if (isSixDigitPin(next)) return null;
    if (next.length < 8) return 'New PIN/password must be at least 8 characters (or a 6-digit PIN).';
    if (next !== confirm) return 'New passwords do not match.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    const problem = validate();
    if (problem) {
      setFeedback({ kind: 'error', text: problem });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      await changePassword(current, next);
      setFeedback({ kind: 'success', text: 'Password updated successfully.' });
      setCurrent('');
      setNext('');
      setConfirm('');
      setTimeout(onClose, 1100);
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Password change failed. Try again.',
      });
    } finally {
      setSaving(false);
    }
  };

  const field = (
    label: string,
    key: string,
    value: string,
    set: (v: string) => void,
    autoComplete?: string
  ) => (
    <div>
      <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
        {label}
      </label>
      <div className="relative">
        <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
        <input
          type={show[key] ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => {
            set(e.target.value);
            if (feedback) setFeedback(null);
          }}
          className="w-full rounded-lg border border-[var(--border-primary)] bg-[var(--bg-primary)] py-2 pl-9 pr-12 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)]"
        />
        <button
          type="button"
          aria-label={show[key] ? 'Hide' : 'Show'}
          onClick={() => toggleShow(key)}
          className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          {show[key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--border-primary)] px-4 py-3">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-[var(--accent-blue)]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Change Password
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="cursor-pointer text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-4">
          <p className="rounded-lg border border-[var(--border-secondary)] bg-[var(--bg-tertiary)]/40 px-3 py-2 font-mono text-[10px] text-[var(--text-muted)]">
            ACCOUNT: <span className="text-[var(--accent-blue)]">{badgeId || '-'}</span>
          </p>

          {field('Current password', 'current', current, setCurrent, 'current-password')}
          {field('New password', 'next', next, setNext, 'new-password')}
          {field('Confirm new password', 'confirm', confirm, setConfirm, 'new-password')}

          {feedback && (
            <div
              className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-[11px] ${
                feedback.kind === 'success'
                  ? 'border-[var(--accent-teal)]/30 bg-[var(--accent-teal)]/10 text-[var(--accent-teal)]'
                  : 'border-[var(--accent-coral)]/30 bg-[var(--accent-coral)]/10 text-[var(--accent-coral)]'
              }`}
            >
              {feedback.kind === 'success' ? (
                <CheckCircle2 className="mt-px h-3.5 w-3.5 shrink-0" />
              ) : (
                <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" />
              )}
              <span>{feedback.text}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-lg border border-[var(--border-primary)] px-3 py-2 text-xs text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--accent-blue)] px-4 py-2 text-xs font-bold uppercase tracking-wider text-white disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
                </>
              ) : (
                'Update Password'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChangePasswordModal;
