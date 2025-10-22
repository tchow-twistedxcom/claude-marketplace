---
name: browser-test
description: Run browser automation tests using Chrome DevTools MCP
---

Execute browser automation and E2E testing workflows using Chrome DevTools.

## Usage

When the user requests browser testing or automation:

1. **Check Browser Connection**: Verify Chrome DevTools is connected at http://localhost:37443
2. **Navigate**: Use chrome-devtools MCP to navigate to target URL
3. **Interact**: Take snapshots, click elements, fill forms, take screenshots
4. **Validate**: Check for expected elements, console errors, network issues
5. **Report**: Provide test results with screenshots/snapshots as needed

## Chrome DevTools Tools Available

- `navigate_page` - Navigate to URL
- `take_snapshot` - Get page structure (text-based, accessible)
- `take_screenshot` - Capture visual state
- `click` - Click elements
- `fill` - Fill form inputs
- `wait_for` - Wait for text to appear
- `list_console_messages` - Check for console errors
- `list_network_requests` - Analyze network activity
- `evaluate_script` - Run JavaScript in page context

## Examples

**User:** "Test the login form"
**Action:** Navigate → Take snapshot → Fill credentials → Click submit → Validate

**User:** "Check for console errors"
**Action:** Navigate → List console messages → Report errors

**User:** "Take screenshot of homepage"
**Action:** Navigate → Take screenshot → Return image
