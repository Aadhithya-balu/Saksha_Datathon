"""Face-recognition isolation boundary (Issue #228).

Holds the synthetic DEMO dataset, the local recognition engine, the optional
Zoho Catalyst/Zia face-analytics adapter, the repository/storage abstraction,
and the high-level service that routes call. Everything under this package is a
self-contained enhancement: it does not import or alter the existing
crime/FIR/evidence/investigation/AI workflows.
"""
