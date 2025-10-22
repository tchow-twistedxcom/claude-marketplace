---
name: e2e-testing-patterns
description: "Best practices and patterns for end-to-end browser testing using Chrome DevTools MCP. Use when implementing browser automation, visual regression testing, or user journey validation."
license: MIT
---

# E2E Testing Patterns with Chrome DevTools

## Core Testing Patterns

### 1. Page Object Pattern
Encapsulate page interactions for maintainability:

```markdown
## Login Page Actions
1. Navigate to /login
2. Take snapshot to locate form elements
3. Fill username field
4. Fill password field
5. Click submit button
6. Wait for dashboard text to appear
```

### 2. Snapshot-First Approach
Always take snapshot before interactions to understand page structure:

```markdown
1. take_snapshot() - Get accessible tree
2. Identify element UIDs from snapshot
3. Use UIDs for click/fill operations
4. Verify state changes with new snapshot
```

### 3. Visual Validation
Combine snapshots with screenshots for comprehensive validation:

```markdown
1. take_snapshot() - Structural validation
2. take_screenshot() - Visual validation
3. list_console_messages() - Error detection
4. list_network_requests() - Performance check
```

## Common Workflows

### Form Testing Workflow
1. Navigate to form page
2. Take snapshot to find form elements
3. Fill all required fields
4. Take screenshot (before submission)
5. Submit form
6. Wait for success message
7. Verify redirect/response
8. Check console for errors

### User Journey Testing
1. Define journey steps (login → browse → action → logout)
2. For each step:
   - Navigate
   - Take snapshot
   - Perform actions
   - Validate expected state
3. Capture screenshots at key points
4. Report any console errors or failed requests

### Visual Regression Testing
1. Baseline: Take screenshot of stable page
2. Make changes
3. Comparison: Take new screenshot
4. Report visual differences
5. Validate no console errors introduced

## Error Handling

### Console Error Detection
```markdown
After each significant action:
1. list_console_messages(types=["error", "warn"])
2. Report any new errors
3. Provide context (URL, action performed)
```

### Network Issue Detection
```markdown
For critical paths:
1. list_network_requests(resourceTypes=["xhr", "fetch"])
2. Check for 4xx/5xx status codes
3. Verify expected API responses
4. Report failed requests with details
```

## Best Practices

1. **Always Use Snapshots First**: More reliable than screenshots for element identification
2. **Wait for Dynamic Content**: Use `wait_for()` with specific text, not arbitrary delays
3. **Verify State Changes**: Take snapshot before and after actions to confirm changes
4. **Check Console Always**: Include console check in every test workflow
5. **Network Validation**: Monitor network for critical user actions
6. **Screenshot Evidence**: Capture screenshots for visual validation and debugging
7. **Clear Error Reporting**: Include URL, action, and error details in reports

## Performance Testing

### Core Web Vitals Check
```markdown
1. Navigate to page
2. performance_start_trace(reload=true, autoStop=true)
3. Wait for trace completion
4. performance_stop_trace()
5. Report LCP, FID, CLS scores
6. Provide optimization recommendations
```

### Load Time Analysis
```markdown
1. Navigate to page
2. list_network_requests()
3. Analyze:
   - Total requests
   - Largest resources
   - Slow requests (>1s)
   - Failed requests
4. Report bottlenecks
```

## Accessibility Testing

### Automated Accessibility Check
```markdown
1. take_snapshot(verbose=true) - Gets full a11y tree
2. Analyze snapshot for:
   - Missing ARIA labels
   - Unlabeled form inputs
   - Images without alt text
   - Buttons without accessible names
3. Report accessibility issues
```

## Integration with CI/CD

### Test Suite Pattern
```markdown
Test Suite: Critical User Journeys
├─ Test 1: User Registration
│  ├─ Navigate → Fill form → Submit → Verify
│  └─ Screenshot + Console check
├─ Test 2: User Login
│  ├─ Navigate → Login → Verify dashboard
│  └─ Screenshot + Console check
└─ Test 3: Core Feature
   ├─ Navigate → Action → Verify result
   └─ Screenshot + Console check

Final Report:
- Pass/Fail status
- Screenshots of failures
- Console errors
- Performance metrics
```
