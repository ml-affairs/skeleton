# Architecture Decision Records

Skeleton ADRs record durable decisions about runtime evidence, artifact
contracts, report semantics, integration seams, and package boundaries.

Each ADR should include a Mermaid diagram using this shared color palette:

```mermaid
flowchart LR
    decision[Decision]
    evidence[Runtime evidence]
    artifact[Artifact contract]
    report[Human report]
    integration[Integration]
    risk[Risk or constraint]

    evidence --> decision --> artifact --> report --> integration
    decision --> risk

    classDef decision fill:#EDE9FE,stroke:#7C3AED,color:#0F172A
    classDef evidence fill:#DCFCE7,stroke:#16A34A,color:#0F172A
    classDef artifact fill:#DBEAFE,stroke:#2563EB,color:#0F172A
    classDef report fill:#FCE7F3,stroke:#DB2777,color:#0F172A
    classDef integration fill:#FEF3C7,stroke:#D97706,color:#0F172A
    classDef risk fill:#FEE2E2,stroke:#DC2626,color:#0F172A

    class decision decision
    class evidence evidence
    class artifact artifact
    class report report
    class integration integration
    class risk risk
```

Use the same class names and color codes across ADR diagrams so readers can scan
decisions consistently.
