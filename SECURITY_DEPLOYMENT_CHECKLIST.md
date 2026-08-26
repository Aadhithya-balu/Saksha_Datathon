# SAKSHA production security checklist

Complete this checklist before each production deployment. Do not use the
development `.env.example` values as production credentials.

## Application and transport

- [ ] `APP_ENV=production`, `APP_DEBUG=false`, and `DEBUG=false`.
- [ ] HTTPS is terminated by a trusted proxy/load balancer; HTTP is redirected
  before reaching users.
- [ ] `ALLOWED_ORIGINS` lists only exact production frontend origins (no `*`
  and no local development origins).
- [ ] Health probes use `/health/live` and `/health/ready`; do not expose
  debug endpoints or interactive API docs publicly unless access controlled.

## Identity and access

- [ ] Set `JWT_SECRET_KEY` to a unique secret generated with
  `secrets.token_urlsafe(48)`; it must never be committed or shared.
- [ ] Keep access tokens short-lived and use the configured refresh-token
  rotation/revocation flow.
- [ ] Provision least-privilege roles and review admin accounts regularly.
- [ ] Ensure the audit-log database table is retained, backed up, and writable
  only by the backend database role.

## Datastores and external services

- [ ] Use PostgreSQL over TLS with a non-default, least-privilege application
  database user; production startup rejects SQLite and common credentials.
- [ ] Use a non-default Neo4j password and restrict the database network path
  to the backend only.
- [ ] Keep Supabase service-role keys server-side. Frontend builds may contain
  only public values such as the Supabase URL and anon key.
- [ ] Enable Supabase RLS/storage policies appropriate to the deployment; do
  not make evidence buckets public.
- [ ] Store LLM provider keys only in backend secret storage and verify any
  provider data-retention agreement required for police data.

## Files, monitoring, and resilience

- [ ] Configure private persistent object storage for evidence; verify upload
  size/type limits and authenticated download access.
- [ ] Configure reverse-proxy rate limits for multi-instance deployments (the
  in-process limiter is per backend instance).
- [ ] Collect sanitized application/audit logs, alert on repeated login and
  authorization failures, and never log credentials or tokens.
- [ ] Test backup restoration for PostgreSQL, Neo4j, and object storage.
- [ ] Run backend security tests, frontend production build, dependency scans,
  and a secrets scan in CI before release.
