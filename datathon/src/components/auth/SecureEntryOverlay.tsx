import React from 'react';
import { createRoot } from 'react-dom/client';
import EntryOverlay from './EntryOverlay';

/**
 * SecureEntryOverlay — post-authentication handoff transition.
 *
 * Rendered imperatively on document.body so it survives the
 * Login → Dashboard swap that happens the moment the session
 * is committed in the auth store. Plays a short, professional
 * sequence: IDENTITY VERIFIED → SECURE SESSION INITIALIZING,
 * then removes itself to reveal the platform underneath.
 */
export const showSecureEntry = (badgeId: string, clearance?: string): void => {
  if (document.getElementById('saksha-entry-overlay')) return;

  const host = document.createElement('div');
  host.id = 'saksha-entry-overlay';
  document.body.appendChild(host);

  const root = createRoot(host);
  const cleanup = () => {
    root.unmount();
    host.remove();
  };

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  root.render(
    <React.StrictMode>
      <EntryOverlay badgeId={badgeId} clearance={clearance || 'AUTHORIZED'} reduced={reduced} />
    </React.StrictMode>
  );

  // Safety net — never leave the overlay stranded.
  window.setTimeout(() => {
    if (document.getElementById('saksha-entry-overlay')) cleanup();
  }, 6000);
};

export default showSecureEntry;
