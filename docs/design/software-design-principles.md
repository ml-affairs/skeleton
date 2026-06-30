# Software Design Principles Skeleton Promotes

## Status

Draft.

## Why This Exists

Skeleton is not neutral about software design. The report can only be useful for
large Python systems if it turns runtime evidence into concepts that developers
already use to reason about maintainable software: actors, use cases, ports,
adapters, repositories, services, external resources, and dependency direction.

That does not mean Skeleton should force one framework or one directory layout.
It does mean Skeleton should make maintainable shapes easier to see and tangled
shapes easier to question.

## Literature Behind The Direction

Skeleton's design vocabulary should stay grounded in established ideas:

- The Zen of Python values explicitness, readability, simple explanations, and
  namespaces. Those ideas map directly to Skeleton's preference for named actors
  and clear ownership boundaries.
- Ports and adapters, also called hexagonal architecture, separates application
  logic from user interfaces, databases, services, queues, files, clocks, and
  other external devices. Skeleton should make those boundary crossings visible.
- Domain-driven design gives useful names for large systems: bounded contexts,
  entities, value objects, aggregates, repositories, domain services, and
  application services. Skeleton should not require DDD, but it should render
  code in a way that makes these ideas recognizable.
- Repository and unit-of-work patterns give Python projects a practical way to
  keep business logic decoupled from persistence. Skeleton should depict those
  objects as architectural actors rather than hiding them as generic call nodes.
- The C4 model reminds us that architecture has levels. Skeleton's v0 graph is
  mostly a runtime component/code view, but it should leave room for future
  context and container views.

Useful source material:

- Python PEP 20, The Zen of Python: <https://peps.python.org/pep-0020/>
- Alistair Cockburn, Hexagonal Architecture: <https://alistair.cockburn.us/hexagonal-architecture/>
- Architecture Patterns with Python: <https://www.cosmicpython.com/book/chapter_02_repository>
- Martin Fowler, Repository: <https://martinfowler.com/eaaCatalog/repository.html>
- Martin Fowler, Bounded Context: <https://martinfowler.com/bliki/BoundedContext.html>
- C4 Model: <https://c4model.com/>

## The Core Rule

Represent architectural actors, not every implementation artifact.

A Python module can be one of two things in the default visual model:

- a host for one or more class actors
- a module actor containing public helper functions

It should not be both at the same level in the graph. If `service.py` exists
only to host `Greeter`, the graph should show `Greeter`, not `service` beside
`Greeter`. The module path is still important metadata, but it is not a peer
actor.

The same rule applies to entrypoints. `entrypoint`, `service`, `repository`, and
`adapter` are often roles. They should usually appear as roles on actors unless
the codebase has a real object that owns that responsibility.

## Patterns Skeleton Should Respect

### Application Services

Application services coordinate a use case. They are allowed to call domain
objects, repositories, ports, and adapters, but should avoid burying business
rules in framework or I/O details.

Skeleton should show:

- fan-out from an application service to domain actors and ports
- safe argument summaries entering the use case
- external resources reached through adapters
- whether the service is becoming a transaction script or orchestration hub

### Domain Objects

Domain entities and value objects should carry business behavior, not only data.
Skeleton should make rich domain behavior visible when public methods call other
domain behavior or enforce rules.

Skeleton should help spot:

- anemic models where most behavior lives outside the domain
- domain objects that directly call databases, HTTP clients, queues, files, or
  environment variables
- domain actors with surprising fan-out to infrastructure

### Ports And Adapters

A port is a purpose-shaped boundary: "load customer", "publish event", "charge
card", "send email", "read model state". An adapter is the technology-specific
implementation of that boundary.

Skeleton should represent external communication as boundary edges:

- inbound adapters drive the application: CLI, web route, worker, scheduled job,
  test harness
- outbound adapters are driven by the application: database, filesystem, HTTP,
  queue, cache, model provider, email, clock, random source
- port/protocol abstractions should be shown separately from concrete adapters
  when runtime evidence makes both visible

### Repositories And Units Of Work

Repositories should look like collection-like access to domain objects, not like
SQL, ORM, file, or network code leaking into the domain. A unit of work should
make transaction boundaries visible.

Skeleton should show:

- which actors load or save domain objects
- commit/rollback-like boundaries when observable
- calls from application services into repositories
- accidental calls from domain objects into repositories

### Dependency Injection And Composition Roots

Dependency injection is valuable because it makes relationships explicit and
swappable. Skeleton should make constructor wiring and runtime collaboration
understandable without forcing decorators.

Skeleton should show:

- object instances when they clarify ownership or lifecycle
- which actor was injected into which orchestrator
- concrete adapters selected by the composition root
- dependency direction at runtime

### I/O Decoupled From Business Logic

I/O is not bad; hidden I/O is bad. Large systems need databases, files, network
calls, queues, clocks, model providers, and environment access. The maintainable
shape is to isolate those operations at boundaries and call them through named
ports or adapters.

Skeleton should eventually depict I/O as first-class external resources:

- `database:postgres`
- `filesystem:/path`
- `http:api.stripe.com`
- `queue:orders`
- `cache:redis`
- `model:openai`
- `clock`
- `environment`

The report should distinguish:

- pure or mostly pure business actors
- boundary actors that translate to or from the outside world
- external resources that the Python process touches
- unsafe crossings where business logic reaches directly into I/O

## What Skeleton Should Make Easy To See

- Which actor starts a workflow.
- Which actor owns the business behavior.
- Which actors perform I/O.
- Which calls cross an architectural boundary.
- Which actors have high fan-in or fan-out.
- Which actors are central coordinators.
- Which concrete adapter was used at runtime.
- Which public methods define the workflow path.
- Which values crossed boundaries, safely summarized and redacted.

## What Skeleton Should Avoid Encouraging

- Treating every file, class, function, and instance as equal graph nodes.
- Showing module and class peers when the module simply hosts the class.
- Making private helper calls look like architecture.
- Normalizing direct database, filesystem, network, or environment access from
  domain logic.
- Confusing framework entrypoints with application actors.
- Hiding external resources behind generic method-call edges.
- Making the graph visually impressive but semantically vague.

## Visual Representation Rules

Default actor graph:

- Show class actors.
- Show module actors only when the module does not host class actors.
- Show entrypoint, service, repository, adapter, and port as roles when possible.
- Hide methods until focus or replay.
- Collapse function-level runtime calls into actor-level edges.
- Keep raw function and event evidence available in the inspector.

Metrics:

- Node size may encode call count, fan-in, fan-out, and approximate LOC.
- Edge width may encode observed call count.
- Edge color or style should distinguish ordinary internal calls from boundary
  calls and external-resource calls.
- Role badges should clarify entrypoint, service, repository, adapter, port,
  domain actor, and external resource.

Replay:

- Use developer language first: `CheckoutService.reserve_stock called
  InventoryRepository.get`.
- Keep business-language inference optional and evidence-based.
- Make hidden methods appear only when they explain the selected actor or current
  replay event.

## Implications For Skeleton Development

- The snapshot may contain low-level nodes, but the report should present a
  higher-level architecture model by default.
- Do not add visual entities just because a trace event contains them. Ask what
  architectural concept they represent.
- When adding I/O tracing, model the external resource explicitly instead of
  burying it inside a method name.
- Prefer schema fields that preserve evidence and allow later query layers:
  actor id, role, boundary kind, resource kind, event ids, safe examples, and
  dependency direction.
- Tests should cover conceptual rendering rules, not only file generation.

