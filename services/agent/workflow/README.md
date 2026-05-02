# Workflow

Custom state machine for the first version of the Agent.

Initial node order:

1. intent_parser
2. constraint_normalizer
3. context_resolver
4. candidate_search
5. route_feasibility
6. ranking
7. itinerary_composer
8. validator
9. execution_planner

Keep node input/output schemas explicit so the workflow can later be migrated to LangGraph.
