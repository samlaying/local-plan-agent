# Agent Workflow

Initial implementation uses a custom state machine.

```text
intent_parser
  -> constraint_normalizer
  -> context_resolver
  -> candidate_search
  -> route_feasibility
  -> ranking
  -> itinerary_composer
  -> validator
  -> execution_planner
```

Every node should:

- Accept a typed planning state.
- Return a partial state patch.
- Record tool calls.
- Avoid direct HTTP or database access unless explicitly owned by the node.

The later LangGraph migration should map each node to an equivalent graph node with the same state schema.
