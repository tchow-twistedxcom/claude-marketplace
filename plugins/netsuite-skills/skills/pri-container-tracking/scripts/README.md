# PRI Container Tracking Diagnostic Scripts

This directory contains utility scripts for diagnosing and resolving common issues with the PRI Container Tracking system.

## Available Scripts

### 1. reset_stuck_queue.js
**Purpose:** Reset queue entries stuck in "Processing" status

**When to Use:**
- Queue processing appears frozen
- Scheduled scripts running but not making progress
- Queue entries stuck for more than 1 hour

**Deployment:**
1. Upload to File Cabinet: `/SuiteScripts/Diagnostics/`
2. Create Suitelet script record
3. Create deployment (unrestricted, no authentication)
4. Navigate to Suitelet URL

**Usage:**
1. Select queue name from dropdown
2. Click "Reset Stuck Entries"
3. Script resets all entries stuck > 1 hour to "Pending"

### 2. sync_container_dates.js
**Purpose:** Manually sync container ETD/ATA dates to TO/IF

**When to Use:**
- Container dates changed but TO/IF not updated
- Date synchronization failed during normal processing
- Manual date correction needed

**Deployment:**
1. Upload to File Cabinet: `/SuiteScripts/Diagnostics/`
2. Create Suitelet script record
3. Create deployment (unrestricted, no authentication)
4. Navigate to Suitelet URL

**Usage:**
1. Enter Container Internal ID
2. Click "Sync Dates"
3. Script updates TO ship/receipt dates and IF transaction date

### 3. reset_ppo_line_status.js
**Purpose:** Reset Production PO Line from Locked to Available status

**When to Use:**
- Line shows "Locked" (status 2) but no PO exists
- Database corruption or script error caused incorrect status
- Need to regenerate PO for the line

**WARNING:** Only use when verified no PO exists for this line!

**Deployment:**
1. Upload to File Cabinet: `/SuiteScripts/Diagnostics/`
2. Create Suitelet script record
3. Create deployment (restricted to administrators)
4. Navigate to Suitelet URL

**Usage:**
1. Verify line has no linked PO (custrecord_pri_frgt_cnt_pmln_linkedpo is empty)
2. Enter Production PO Line Internal ID
3. Click "Reset Status"
4. Script validates and resets status to Available (1)

## Script Deployment Best Practices

**Security:**
- Deploy diagnostic scripts with appropriate role restrictions
- Consider using login-required deployments for sensitive operations
- Log all administrative actions for audit purposes

**Testing:**
- Always test scripts in Sandbox environment first
- Verify expected behavior with sample data
- Check script execution logs after running

**Monitoring:**
- Review script execution logs regularly
- Set up email alerts for script failures
- Document any manual interventions in NetSuite case notes

## Common Issues Resolved

| Issue | Script | Additional Notes |
|-------|--------|------------------|
| Queue stuck | reset_stuck_queue.js | Check execution logs first |
| Date sync failed | sync_container_dates.js | Verify TO link exists |
| Line incorrectly locked | reset_ppo_line_status.js | Validate no PO before reset |

## Additional Resources

See the skill's reference documentation for:
- Complete troubleshooting workflows
- Root cause analysis procedures
- Integration architecture details
