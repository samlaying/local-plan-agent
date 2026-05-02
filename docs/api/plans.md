# Plans API

## POST /api/plans/preview

Create preview plans from a natural-language planning request.

Input fields:
- `raw_text`
- `origin_location`
- `time_window`
- `participants`
- `preferences`

Output fields:
- `request_id`
- `parsed_request`
- `plans`
- `missing_fields`
- `tool_call_summary`

## POST /api/plans/{plan_id}/actions

Create executable actions after the user selects a plan.

Output fields:
- `plan_id`
- `actions`
- `requires_confirmation`
