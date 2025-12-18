# Feature Implementation Example

End-to-end walkthrough of implementing a new feature using Claude Code.

---

## Scenario

**Request**: "Add a password reset feature to the authentication system"

**Requirements**:
- User can request password reset via email
- Token-based reset link (expires in 1 hour)
- New password validation
- Email notification

---

## Step 1: Plan the Implementation

### Enter Plan Mode

For non-trivial features, start with planning:

```
User: "Add password reset functionality to the app"

Claude: This is a multi-component feature. Let me enter plan mode to design
the implementation before coding.

[EnterPlanMode]
```

### Explore Existing Patterns

```
Task (Explore): "How is authentication implemented? Find auth-related files,
understand the current user model, and identify email service patterns."
```

Findings:
- Auth in `src/auth/` using JWT
- User model has `passwordHash` field
- Email service exists at `src/services/email.ts`
- API routes in `src/api/auth.ts`

### Design with Plan Agent

```
Task (Plan): "Design password reset feature that fits existing auth patterns.
Existing: JWT auth in src/auth/, email service in src/services/email.ts,
user model in src/models/user.ts, API routes in src/api/auth.ts"
```

Plan output:
1. Add `resetToken` and `resetExpires` to User model
2. Create `/api/auth/forgot-password` endpoint
3. Create `/api/auth/reset-password` endpoint
4. Add email template for reset link
5. Add password validation utility

---

## Step 2: Track Progress

### Create Todo List

```
TodoWrite:
1. Add reset fields to User model
2. Create forgot-password endpoint
3. Create reset-password endpoint
4. Add email template
5. Add tests
```

---

## Step 3: Implement Changes

### Update User Model

```
Read: src/models/user.ts

Edit: src/models/user.ts
old_string: export interface User {
  id: string;
  email: string;
  passwordHash: string;
}
new_string: export interface User {
  id: string;
  email: string;
  passwordHash: string;
  resetToken?: string;
  resetExpires?: Date;
}
```

**Mark todo complete**: "Add reset fields to User model" ✓

### Create API Endpoints

Using MultiEdit for multiple related changes in same file:

```
Read: src/api/auth.ts

Edit: src/api/auth.ts
[Add forgot-password endpoint after existing login endpoint]

old_string: // End of auth routes
new_string: // Password reset
router.post('/forgot-password', async (req, res) => {
  const { email } = req.body;
  const user = await db.users.findByEmail(email);

  if (!user) {
    // Don't reveal if email exists
    return res.json({ message: 'If email exists, reset link sent' });
  }

  const token = crypto.randomBytes(32).toString('hex');
  const expires = new Date(Date.now() + 3600000); // 1 hour

  await db.users.update(user.id, { resetToken: token, resetExpires: expires });
  await emailService.sendPasswordReset(email, token);

  return res.json({ message: 'If email exists, reset link sent' });
});

router.post('/reset-password', async (req, res) => {
  const { token, newPassword } = req.body;

  const user = await db.users.findByResetToken(token);
  if (!user || user.resetExpires < new Date()) {
    return res.status(400).json({ error: 'Invalid or expired token' });
  }

  if (!validatePassword(newPassword)) {
    return res.status(400).json({ error: 'Password does not meet requirements' });
  }

  const passwordHash = await bcrypt.hash(newPassword, 10);
  await db.users.update(user.id, {
    passwordHash,
    resetToken: null,
    resetExpires: null
  });

  return res.json({ message: 'Password reset successful' });
});

// End of auth routes
```

**Mark todo complete**: "Create forgot-password endpoint" ✓
**Mark todo complete**: "Create reset-password endpoint" ✓

### Add Email Template

```
Read: src/services/email.ts

Edit: src/services/email.ts
old_string: export const emailService = {
  sendWelcome,
};
new_string: export const emailService = {
  sendWelcome,
  sendPasswordReset: async (email: string, token: string) => {
    const resetUrl = `${process.env.APP_URL}/reset-password?token=${token}`;
    await sendEmail({
      to: email,
      subject: 'Password Reset Request',
      html: `
        <h1>Password Reset</h1>
        <p>Click the link below to reset your password:</p>
        <a href="${resetUrl}">Reset Password</a>
        <p>This link expires in 1 hour.</p>
      `
    });
  },
};
```

**Mark todo complete**: "Add email template" ✓

---

## Step 4: Review Changes

### Run Code Review Agent

```
Task (feature-dev:code-reviewer): "Review the password reset implementation
in src/api/auth.ts and src/services/email.ts for security issues and best practices"
```

Review findings:
- ✓ Token is cryptographically random
- ✓ Doesn't reveal if email exists
- ✓ Token expiration implemented
- ⚠️ Consider rate limiting forgot-password endpoint
- ⚠️ Add logging for security audit

### Apply Review Feedback

```
Edit: src/api/auth.ts
[Add rate limiting and logging]
```

---

## Step 5: Add Tests

```
Read: src/tests/auth.test.ts

Edit: src/tests/auth.test.ts
[Add test cases for password reset]

old_string: describe('Auth API', () => {
new_string: describe('Auth API', () => {
  describe('Password Reset', () => {
    it('sends reset email for valid user', async () => {
      const res = await request(app)
        .post('/api/auth/forgot-password')
        .send({ email: 'test@example.com' });
      expect(res.status).toBe(200);
    });

    it('resets password with valid token', async () => {
      // Create user with reset token
      const user = await createTestUser({ resetToken: 'valid-token' });

      const res = await request(app)
        .post('/api/auth/reset-password')
        .send({ token: 'valid-token', newPassword: 'NewPass123!' });
      expect(res.status).toBe(200);
    });

    it('rejects expired token', async () => {
      const user = await createTestUser({
        resetToken: 'expired-token',
        resetExpires: new Date(Date.now() - 3600000)
      });

      const res = await request(app)
        .post('/api/auth/reset-password')
        .send({ token: 'expired-token', newPassword: 'NewPass123!' });
      expect(res.status).toBe(400);
    });
  });
```

**Mark todo complete**: "Add tests" ✓

---

## Step 6: Verify Implementation

### Run All Tests

```
Bash: npm test

Output:
Auth API
  Login
    ✓ logs in with valid credentials
    ✓ rejects invalid password
  Password Reset
    ✓ sends reset email for valid user
    ✓ resets password with valid token
    ✓ rejects expired token

5 passing (892ms)
```

### Manual Testing

```
Bash: curl -X POST http://localhost:3000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

Output: {"message":"If email exists, reset link sent"}
```

---

## Tool Usage Summary

| Phase | Tool | Purpose |
|-------|------|---------|
| Planning | EnterPlanMode | Complex feature setup |
| Exploration | Task (Explore) | Understand existing code |
| Design | Task (Plan) | Architecture decisions |
| Tracking | TodoWrite | Progress management |
| Implementation | Read + Edit | Code changes |
| Review | Task (code-reviewer) | Quality check |
| Testing | Edit + Bash | Add and run tests |

---

## Key Takeaways

1. **Plan before coding**: Use EnterPlanMode for multi-component features
2. **Explore existing patterns**: Match new code to existing conventions
3. **Track progress**: TodoWrite keeps work organized
4. **Review before finishing**: Catch issues early with code-reviewer
5. **Test thoroughly**: Add tests for success and failure cases

---

*See also: [agent-catalog.md](../references/agent-catalog.md) for agent selection*
