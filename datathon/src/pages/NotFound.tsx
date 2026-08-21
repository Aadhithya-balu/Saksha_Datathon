function NotFound() {
  const baseUrl = import.meta.env.BASE_URL || '/';

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4">
      <div className="max-w-xl w-full text-center rounded-2xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] p-8 shadow-xl">
        <p className="text-sm font-mono text-[var(--text-muted)]">ERROR 404</p>
        <h1 className="mt-2 text-4xl font-bold text-[var(--text-primary)]">Page Not Found</h1>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">
          The page you are looking for does not exist. Please return to the main page.
        </p>
        <a
          href={baseUrl}
          className="inline-flex mt-6 px-5 py-2.5 rounded-lg bg-[var(--accent-blue)] text-white font-semibold hover:opacity-90 transition-opacity"
        >
          Go to Main Page
        </a>
      </div>
    </div>
  );
}

export default NotFound;
