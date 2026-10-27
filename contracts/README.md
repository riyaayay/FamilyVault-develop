# Contracts & Interface Specifications

This directory contains shared interface contracts, schema definitions, and constant values that unblock cross-service development across the FamilyVault team.

## Shared Contracts
- `schema.sql`: Authoritative PostgreSQL schema DDL with Three-Tier Row Level Security (RLS) policies and UUID mapping documentation. Owned by **Runeet**.
- `MATCH_CONSTANTS.json`: Central biometric constants (`MATCH_THRESHOLD: 0.85`, `EMBEDDING_DIMENSION: 512`). Shared between **Ayushman** and **Ayush**.
- `graph-tree-response.json`: Mock response shape for `GET /api/graph/tree`. Owned by **Riya** to unblock **Anushka**.
- `media-match-response.json`: Mock response shape for biometric inbox matches. Owned by **Ayushman** to unblock **Raghuvendra**.

## Contract Change Policy
Whenever any file in this directory changes, the owner must post an immediate notification in the `#familyvault-dev` Slack/Discord channel on the same working day.
