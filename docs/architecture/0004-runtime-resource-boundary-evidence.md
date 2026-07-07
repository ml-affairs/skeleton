# Runtime Resource Boundary Evidence

## Status

Accepted

## Diagram

```mermaid
flowchart LR
    actor[Project-local actor]
    decision[Capture bounded<br/>resource calls]
    resource[Resource actor<br/>stdout/files/db]
    external[External service<br/>network]
    report[Boundary-visible report]
    risk[Do not trace<br/>full dependencies]

    actor --> decision
    decision --> resource
    decision --> external
    resource --> report
    external --> report
    decision --> risk

    classDef decision fill:#EDE9FE,stroke:#7C3AED,color:#0F172A
    classDef evidence fill:#DCFCE7,stroke:#16A34A,color:#0F172A
    classDef artifact fill:#DBEAFE,stroke:#2563EB,color:#0F172A
    classDef report fill:#FCE7F3,stroke:#DB2777,color:#0F172A
    classDef integration fill:#FEF3C7,stroke:#D97706,color:#0F172A
    classDef risk fill:#FEE2E2,stroke:#DC2626,color:#0F172A

    class decision decision
    class actor,resource,external evidence
    class report report
    class risk risk
```

## Context

Important architecture behavior often crosses out of Python project-local
frames: stdout, filesystem access, SQLite, network sockets, queues, caches,
clocks, random sources, and model providers. If those operations are hidden
inside ordinary call edges, the report cannot show where I/O enters a workflow
or whether business logic is coupled directly to infrastructure.

At the same time, tracing the whole standard library or third-party stack would
turn Skeleton into a noisy dependency trace.

## Decision

Skeleton records a small allow-list of runtime resource boundary events only
while project-local code is active on the trace stack.

The snapshot and report project these as explicit resource or external-service
actors rather than burying them inside method labels. Current resource evidence
includes stdout, filesystem operations, SQLite/database operations, and basic
network socket calls.

External network endpoints are modeled as external services. Local resources
such as stdout, filesystems, and databases are modeled as resources.

## Consequences

The report can show hidden I/O and boundary crossings without pulling the full
dependency graph into the architecture view.

Resource evidence remains bounded and conservative. Adding a new resource kind
requires a clear product reason, tests, safe value summaries, and documentation
of what is captured.

This supports quality signals and future query features such as "which actors
touched external resources in this scenario?"
