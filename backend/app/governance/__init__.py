"""Governance slice for DocGuardian AI.

ACL enforcement, document health/importance derivation, approval + provenance,
metrics aggregation, and the persistence that backs them. Pure logic
(``acl``, ``health``, ``metrics``) is import-safe and has no DB dependency; the
``store`` and ``service`` modules talk to Postgres.
"""
