# Runtime Replay vs Knowledge Graphs

## Status

Reference note.

## Context

Graphify is a useful adjacent project to study because it presents code
understanding as a queryable graph for AI coding assistants. Its public product
page describes a multi-modal knowledge graph builder that combines Tree-sitter
static analysis, LLM-driven semantic extraction, NetworkX graph construction,
Leiden clustering, and assistant commands such as query, path, and explain.

That is close enough to Skeleton's graph and LLM-readable ambitions to be worth
learning from, but it is not the same product category.

## Product Boundary

Skeleton should be the runtime counterpart to repository knowledge graph tools:

> Graph tools map the repository's knowledge. Skeleton replays the application's behavior.

Skeleton's durable product identity is runtime architecture replay. It should
show what actually happened in a scenario: which modules were loaded, which
object instances handled public methods, which actors called each other, what
safe arguments and returns were observed, and how the runtime graph changed over
time.

Graphify-like tools answer:

- What does this repository contain?
- What concepts, docs, diagrams, and code symbols are connected?
- Which files, APIs, or concepts are central?
- What should an AI assistant read before editing?

Skeleton should answer:

- What happened when this scenario ran?
- Which runtime actors collaborated?
- Which calls crossed architectural boundaries?
- Which instance produced this return value?
- Where did I/O enter the workflow?
- Which runtime edges, fan-in, fan-out, and object lifecycles explain the behavior?

## Comparison

| Area | Static or multi-modal knowledge graph tools | Skeleton |
| --- | --- | --- |
| Primary evidence | Static source, documentation, papers, diagrams, extracted concepts | Runtime call and return events |
| Main time model | Repository state | Ordered scenario replay |
| Graph meaning | Knowledge graph of concepts, files, symbols, and semantic links | Observed architecture graph of modules, instances, functions, methods, calls, returns, and resources |
| Object identity | Usually not central | Central: run-local instances and method ownership |
| Value evidence | Usually semantic summaries | Safe argument and return summaries |
| Best question | "What does this codebase mean?" | "What happened in this execution?" |
| LLM role | Semantic extraction and assistant retrieval | Evidence consumer first; extraction later only where it preserves privacy and correctness |
| Risk | Static graph can imply behavior that did not run | Runtime graph can miss behavior that was not exercised |

The strongest future direction is not to choose one forever. Skeleton can later
blend static context into runtime replay, but runtime evidence must remain the
source of truth for scenario behavior.

## Lessons To Borrow

Skeleton should borrow these product patterns:

- A crisp pipeline story: `run -> trace -> snapshot -> workflow -> report -> query`.
- Durable artifacts that can be inspected independently.
- A query surface over saved graph data rather than only an HTML report.
- Runtime equivalents of centrality analysis: highest fan-in, highest fan-out,
  busiest actors, most frequently crossed boundaries, and surprising edges.
- Assistant-friendly commands such as `skeleton query`, `skeleton path`, and
  `skeleton explain`.
- Reproducible examples with concrete metrics: events, actors, calls, edges,
  fan-in/fan-out, and scenario summaries.
- Strong safety language: no raw object dumps, secret redaction, path
  containment, output escaping, bounded capture, and clear outbound-network
  behavior.
- Human-readable report artifacts such as `workflow.md` that explain the graph
  without requiring HTML scraping.

## Things Not To Copy Yet

Skeleton should avoid diluting its runtime-replay wedge:

- Do not become a generic static knowledge graph builder.
- Do not make Tree-sitter or multi-language static parsing the core v0 story.
- Do not send source code or runtime values to an LLM by default.
- Do not add semantic extraction before the trace, snapshot, and replay schema
  are stable enough to serve as evidence.
- Do not render every repository concept as an equal graph node. Preserve the
  actor model: modules as containers, runtime instances as actors, public
  functions and methods as observed behavior, and external resources as
  boundaries.
- Do not let query features imply coverage that the runtime scenario did not
  exercise.

## Runtime Query Direction

The eventual query interface should feel graph-native without requiring users to
run a graph database:

```text
skeleton query "which actors called PaymentGateway?"
skeleton path OrderService PaymentGateway
skeleton explain --event 42
skeleton compare run-a run-b
```

Useful runtime queries include:

- show calls from actor A to actor B
- show all public methods observed on one runtime instance
- show fan-in and fan-out at event N
- show external resources touched by this scenario
- show the path that produced a return value
- show surprising cross-boundary calls
- compare two runs and explain changed runtime edges

This requires snapshot data to keep stable ids, event ranges, edge kinds,
actor/resource roles, safe examples, and replay position semantics.

## Recommended Roadmap

Near-term improvements should strengthen the runtime story:

1. Stabilize and document `snapshot.json` as a graph contract.
2. Add a query API over `snapshot.json`.
3. Improve `workflow.md` with scenario summary, actors, calls, returns,
   surprising edges, and trace gaps.
4. Add runtime architecture metrics: fan-in, fan-out, call count, actor
   centrality, boundary crossings, and instance lifetimes.
5. Add I/O/resource representation for databases, files, HTTP services, queues,
   caches, clocks, randomness, environment access, and model providers.
6. Ship realistic sample scenarios showing controllers, services, repositories,
   adapters, domain objects, and external resources.
7. Add assistant integration only after the saved evidence is useful without an
   assistant.

Longer-term static integration can enrich the replay, but it should remain
clearly labeled as static context. Runtime evidence should continue to determine
which actors, calls, values, returns, and resources appeared in a scenario.
