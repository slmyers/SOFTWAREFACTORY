# Executor / Reviewer Browser Prompt

Use the `browser_action` tool whenever a spec involves web UI, E2E tests, or
browser-based validation.  The Playwright MCP server is auto-discovered via the
MCP registry (default: `http://localhost:3000`; override with
`MCP_SERVER_PLAYWRIGHT_MCP`).

## Supported Actions

| Action          | Key Params                              | Purpose                          |
|-----------------|----------------------------------------|----------------------------------|
| `navigate`      | `url`                                  | Open a URL                       |
| `snapshot`      | *(none)*                               | Accessibility tree (prefer over screenshot for actions) |
| `screenshot`    | `filename` (optional)                  | Capture viewport as PNG          |
| `click`         | `ref`, `element`                       | Click an element                 |
| `type`          | `ref`, `text`                          | Type into a focused element      |
| `fill`          | `ref`, `value`                         | Fill a form field                |
| `press_key`     | `key`                                  | Press a keyboard key             |
| `hover`         | `ref`, `element`                       | Hover over an element            |
| `select_option` | `ref`, `values`                        | Select dropdown option(s)        |
| `wait_for`      | `text` or `time`                       | Wait for text or N seconds       |
| `evaluate`      | `function`                             | Run JS in the page               |
| `close`         | *(none)*                               | Close the browser page           |

## Workflow for Web Specs

1. **Navigate** to the app under test.
2. **Snapshot** to get the accessibility tree (use `ref` values for actions).
3. **Interact** (click / fill / type) as needed.
4. **Assert** by checking snapshot text or using `evaluate` to query the DOM.
5. **Screenshot** for visual evidence (attached to quality-score as evidence).
6. **Close** when done.

## Quality Score Integration

- Each successful browser session with a recorded video increments
  `Browser E2E Coverage` in `harness/quality-score.md`.
- Accessibility-tree snapshots count toward the `Accessibility Tree` metric.
- Failing browser assertions should set `invariants_ok = false` in AgentState.

## Example

```python
browser_action("navigate", {"url": "http://localhost:3001"})
browser_action("snapshot")
browser_action("fill", {"ref": "e5", "value": "Buy milk"})
browser_action("click", {"ref": "e8", "element": "Add"})
browser_action("snapshot")   # verify item appears
browser_action("screenshot", {"filename": "todo-added.png"})
browser_action("close")
```
