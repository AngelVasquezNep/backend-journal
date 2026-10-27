<!--
Sync Impact Report
Version change: unversioned scaffold -> 1.0.0 (initial adoption)
Modified principles:
- Unfilled principle slots -> I. Question-Answering Purpose
- Unfilled principle slots -> II. Validate Every User Input
- Unfilled principle slots -> III. Microservices Architecture
- Unfilled principle slots -> IV. Complete Code Documentation
Added sections:
- Architecture and Interface Constraints
- Development Workflow and Quality Gates
- Governance rules and version metadata
Removed sections: unused fifth principle placeholder; no adopted principles removed.
Deferred TODOs: none.
Review note: Remove this temporary report before committing the constitution.
-->

# Taskify Constitution

## Core Principles

### I. Question-Answering Purpose

Taskify MUST provide responses to users' questions. Every feature specification MUST describe
how it supports asking questions, producing responses, or operating that capability. Question
and response behavior MUST have explicit acceptance criteria, including how the application
handles a question it cannot answer. This keeps development aligned with Taskify's purpose.

### II. Validate Every User Input

Every user-controlled input MUST be validated on the server before business processing,
persistence, or use in downstream operations. Validation MUST cover all entry points and
applicable type, format, length, size, range, required-field, and domain constraints. Free-text
questions MUST have explicit acceptance rules, including non-empty content and a maximum
length. Client-side checks MAY improve usability but MUST NOT replace server-side validation.

Each service MUST validate incoming data against its own interface contract, including
user-controlled data forwarded by another service. Invalid input MUST be rejected with an
actionable error that does not expose secrets or internal implementation details. Validation
rules and their valid, invalid, and boundary cases MUST be documented and verified. These
requirements prevent untrusted data from bypassing validation through alternate entry points.

### III. Microservices Architecture

Taskify MUST use independently deployable services with explicit business responsibilities
and documented interfaces. Each service MUST own its business logic and data; other services
MUST access that data through published interfaces rather than directly reading or modifying
its storage. Inter-service communication MUST use explicit request, response, or event
contracts that define schemas, validation rules, and failure behavior.

Contract changes MUST preserve compatibility with active consumers or include a documented
version transition and migration plan. Shared components MUST NOT require services to be
deployed together. These boundaries preserve independent development and deployment.

### IV. Complete Code Documentation

All code MUST be documented and its documentation MUST remain accurate as behavior changes.
Every module, class, function, and method, including internal code, MUST have documentation
describing its purpose and applicable inputs, outputs, errors, and side effects, using the
language's standard documentation conventions. Non-obvious algorithms, constraints, and design
decisions MUST include comments explaining their rationale.

Every service MUST document its responsibility, interfaces, configuration, dependencies,
local setup, execution, testing, and operational failure handling. Interface documentation
MUST include schemas, validation constraints, error responses, and representative examples.
Code changes MUST update affected documentation in the same change so maintainers and
consumers can rely on it.

## Architecture and Interface Constraints

Implementation plans MUST identify service boundaries, data ownership, communication
contracts, and every user-input entry point affected by a change. Each entry point MUST map
to documented validation rules and error behavior. Plans MUST identify affected consumers and
compatibility requirements when service contracts change.

Technology choices MUST support these principles and MUST be recorded with their rationale
in the relevant design documentation. This constitution does not prescribe a programming
language, framework, transport, or database.

## Development Workflow and Quality Gates

Specifications, plans, and tasks MUST demonstrate compliance with the core principles before
implementation begins. Reviewers MUST verify that each change supports Taskify's purpose,
validates affected inputs, preserves service boundaries and contract compatibility, and
includes complete, current documentation.

Before merge, affected validation paths MUST pass checks for accepted, rejected, and boundary
inputs. Changes to inter-service communication MUST pass contract or integration checks for
the affected producer and consumers, including defined failure behavior. Review records MUST
identify the checks performed and their results. Unresolved constitutional violations MUST
block merge until the change complies or an approved constitutional amendment takes effect.

## Governance

This constitution is the authoritative source of project principles. Project specifications,
plans, tasks, implementation decisions, and reviews MUST comply with it. Conflicts MUST be
resolved in favor of the constitution or through an explicit amendment before proceeding.

Amendments MUST be proposed in a reviewed change to this document. The proposal MUST explain
the rationale, identify affected principles and artifacts, and include a migration plan when
existing implementations or contracts require changes. A project maintainer MUST approve the
amendment before it takes effect. Affected project artifacts MUST then be brought into
alignment through explicit follow-up work.

Constitution versions MUST follow semantic versioning: MAJOR for incompatible principle
removals or redefinitions; MINOR for new principles, sections, or materially expanded
guidance; PATCH for clarifications that do not change obligations. Every amendment MUST
update the version and last-amended date while preserving the original ratification date.
Compliance MUST be reviewed during specification and planning reviews and for every pull
request. The initial adoption date is recorded below.

**Version**: 1.0.0 | **Ratified**: 2026-10-20 | **Last Amended**: 2026-10-20
