---
name: pri-container-tracking
description: Comprehensive expertise for debugging, diagnosing, and understanding the Prolecto PRI Container Tracking system (Bundle 125246). Includes deep knowledge of 23+ Application Settings that control field mappings, workflows, and system behavior. This skill should be used when working with PRI freight containers, production purchase orders, landed cost allocation, item versions, container distribution workflows, or PRI configuration/customization in NetSuite. Essential for troubleshooting PRI-related issues, understanding data models, analyzing backend processing, configuring application settings, or planning system modifications.
---

# PRI Container Tracking Expert

## Overview

Provide specialized knowledge and diagnostic capabilities for the **Prolecto PRI Container Tracking System** (Bundle 125246), a comprehensive NetSuite SuiteBundle managing freight container logistics, production purchase order orchestration, and advanced landed cost allocation.

## When to Use This Skill

Activate this skill when:

- **Debugging PRI Issues:** Troubleshooting errors, failures, or unexpected behavior in PRI Container Tracking
- **Understanding System Architecture:** Analyzing custom records, data models, or workflow logic
- **Diagnosing Data Issues:** Investigating locked lines, orphaned transactions, queue failures, or sync problems
- **Planning Modifications:** Preparing to customize or extend PRI functionality
- **Training/Documentation:** Learning how the PRI system works or creating user guides
- **Upgrade Planning:** Assessing impact of PRI bundle updates or NetSuite upgrades
- **Integration Analysis:** Understanding how PRI connects with other systems or bundles

**Keywords that trigger this skill:**
- PRI Container, freight container, vessel, carrier
- Production PO, blanket PO, item version
- Landed cost allocation, LC template
- IR to TO Linker, container distribution
- Bundle 125246, Bundle 132118 (Infrastructure), Bundle 168443 (RSM)
- Queue stuck, dates not syncing, line locked
- Application settings, field mapping configuration
- PRI_AS_Engine, SYNCSRCDEF, customrecord_pri_app_setting
- Twisted X PRI customizations

## System Overview

**Scope:**
- 47 JavaScript files (~20,835 lines of code)
- 10 custom record types with 100+ custom fields
- 35 active script deployments
- 4 major subsystems: Production Management, Container Logistics, In-Transit Linking, Landed Cost

**Critical Dependency:**
- Bundle 132118 (Prolecto Infrastructure) - REQUIRED for Queue Manager and App Settings

**No External Integrations:**
- Pure NetSuite architecture (no EDI/shipping carrier APIs)

## Core Capabilities

### 1. Application Settings Configuration

Understand and configure the 23+ PRI Application Settings that control system behavior dynamically:

**What are Application Settings?**
- Custom record type: `customrecord_pri_app_setting`
- JSON-based configuration system for dynamic behavior control
- Controls field mappings, workflows, validations, status logic, and UI behavior
- Environment-specific targeting (Production, Sandbox, Account ID)
- Loaded by PRI_AS_Engine with per-execution caching

**Key Application Settings:**

| Setting ID | Name | Purpose | Type |
|------------|------|---------|------|
| **250** | TrnfrOrd Line Field Mapping From Container | Maps Container fields → TO line fields | JSON Object |
| **251** | Landed Cost Template Search | Default LC template lookup | Saved Search ID |
| **252** | Container Status Values | Status progression definitions | JSON Array |
| **253** | Production PO Search | Production PO saved search | Saved Search ID |
| **254** | Role Permissions | User role access control | JSON Object |
| **255** | Workflow Actions | Automated workflow triggers | JSON Object |
| **257** | Custom Field Mappings (Non-Date) | Additional field sync rules | JSON Object |
| **258** | Body Field Mappings | Header-level field mappings | JSON Object |

**Field Mapping Configuration:**

Application Setting 250 controls Transfer Order line-level date synchronization:

```json
{
  "source_mapObj": {
    "expectedreceiptdate": "custrecord_pri_frgt_cnt_date_dest_est",
    "expectedshipdate": "custrecord_pri_frgt_cnt_date_sail"
  }
}
```

**How Field Mappings Work:**
1. Container date updated → triggers afterSubmit event
2. Script loads Application Setting via PRI_AS_Engine
3. SYNCSRCDEF class (PRI_SourceFieldValues.js) parses JSON mapping
4. `renderLineFld()` method applies mapping to TO lines
5. All TO line dates updated with Container values

**Common Configuration Issues:**

| Issue | Root Cause | Fix |
|-------|------------|-----|
| TO line dates not syncing | Hardcoded logic bypasses Setting 250 | Modify pri_container_ss.js to use SYNCSRCDEF |
| Field mapping not applied | Status gate prevents execution | Remove status check in pri_itemrcpt_lib.js |
| Wrong fields mapped | JSON configuration incorrect | Update Application Setting 250 JSON |
| Mapping fails silently | Field ID mismatch | Verify NetSuite field IDs match JSON |

**Configuration Architecture:**

```
Application Settings
├─ Environment Lookup (Account → Sandbox → Global)
├─ PRI_AS_Engine (Loader with caching)
├─ SYNCSRCDEF (Field mapping engine)
└─ Target Scripts (Consumer scripts)
    ├─ pri_container_ss.js (Container events)
    ├─ pri_itemrcpt_lib.js (TO/IR creation)
    └─ pri_trnfrord_ss.js (TO events)
```

**Reference Documentation:**
- **PRI_APPLICATION_SETTINGS_CATALOG.md** (20KB) - Complete settings catalog with all 23+ configurations
- **PRI_APPLICATION_SETTINGS_ARCHITECTURE.md** (27KB) - Configuration system architecture and patterns
- **PRI_APPLICATION_SETTINGS_FIELD_MAPPING_ANALYSIS.md** (20KB) - Deep-dive on field mapping engine

**Modification Workflow:**
1. Load Application Settings Catalog to find relevant setting
2. Review current JSON configuration
3. Update JSON with new field mappings
4. Test in Sandbox environment first
5. Deploy to Production after validation
6. Monitor script execution logs for errors

**Example Use Cases:**
- Add new date field sync: Update Setting 250 JSON
- Change status progression: Modify Setting 252 JSON array
- Add custom field mapping: Update Setting 257 or 258
- Configure role permissions: Edit Setting 254 JSON
- Change default LC template: Update Setting 251 search ID

### 2. Diagnostic Troubleshooting

Use the diagnostic workflow to resolve common issues:

**Step 1: Identify Issue Category**

| Category | Keywords | Primary Reference |
|----------|----------|-------------------|
| **Configuration** | Application settings, field mappings, JSON config | `PRI_APPLICATION_SETTINGS_CATALOG.md` |
| **Architecture** | File structure, modules, dependencies | `PRI_CONTAINER_TRACKING_MASTER_REFERENCE.md` |
| **Data Models** | Custom records, fields, relationships | `PRI_CONTAINER_TRACKING_DATA_MODEL.md` |
| **Backend Logic** | User events, scheduled scripts, workflows | `PRI_CONTAINER_BACKEND_PROCESSING.md` |
| **User Interface** | Suitelets, client scripts, forms | `PRI_CONTAINER_UI_UX_ANALYSIS.md` |
| **Integration** | Bundle dependencies, NetSuite modules | `PRI_CONTAINER_TRACKING_INTEGRATION_ARCHITECTURE.md` |
| **Customizations** | Twisted X modifications, upgrades | `PRI_BUNDLE_CUSTOMIZATION_ANALYSIS.md` |
| **Quick Fixes** | Common errors, diagnostics | `PRI_CONTAINER_QUICK_REFERENCE.md` |

**Step 2: Load Relevant Documentation**

```bash
# Quick lookups for scripts, fields, or record types
grep -i "script_name\|field_id\|record_type" references/PRI_CONTAINER_QUICK_REFERENCE.md

# Find specific error messages
grep -i "error_message" references/PRI_CONTAINER_QUICK_REFERENCE.md

# Search troubleshooting matrix
grep -i "symptom_keyword" references/PRI_CONTAINER_TRACKING_MASTER_REFERENCE.md
```

**Reference File Sizes:**
- Master Reference: 76KB - Start here for troubleshooting workflows
- Backend Processing: 57KB - Detailed automation and event logic
- Integration Architecture: 52KB - Dependencies and integrations
- Data Model: 37KB - Complete entity documentation
- UI/UX Analysis: 35KB - User interface patterns
- Customization Analysis: 31KB - Twisted X modifications
- Application Settings Architecture: 27KB - Configuration system design
- Application Settings Catalog: 20KB - All 23+ settings documented
- Application Settings Field Mapping: 20KB - Field mapping engine deep-dive
- Analysis Summary: 19KB - Executive overview
- Quick Reference: 13KB - Fast lookups

**Step 3: Apply Diagnostic Workflow**

Example diagnostic paths:

```
Issue: Production PO Lines locked unexpectedly
    ↓
1. Load Master Reference > Diagnostic Guide > Issue 1
2. Check SQL: SELECT status, linkedpo FROM customrecord_pri_frgt_cnt_pmln WHERE id = ?
3. If linkedpo empty and status = 2, use reset_ppo_line_status.js
4. Verify line can be edited
```

```
Issue: Container dates not syncing to TO/IF
    ↓
1. Load Master Reference > Issue 3
2. Verify container has TO linked: custrecord_pri_frgt_cnt_trnfrord
3. Check IF exists: SELECT id FROM itemfulfillment WHERE createdfrom = ?
4. Use sync_container_dates.js to manually sync
5. Verify dates updated on TO and IF
```

```
Issue: Queue processing stuck
    ↓
1. Load Master Reference > Issue 6
2. Check queue status: SELECT * FROM customrecord_pri_qm_queue WHERE status = 'Processing'
3. Identify stuck entries (created > 1 hour ago)
4. Use reset_stuck_queue.js
5. Monitor scheduled script execution
```

### 3. System Architecture Understanding

Navigate the system architecture efficiently:

**Data Model Exploration:**
1. Load `PRI_CONTAINER_TRACKING_DATA_MODEL.md` for entity relationships
2. Find specific custom record: grep "customrecord_pri_" references/PRI_CONTAINER_TRACKING_DATA_MODEL.md
3. Understand field purposes and validation rules
4. Trace data flow patterns between entities

**Backend Processing Analysis:**
1. Load `PRI_CONTAINER_BACKEND_PROCESSING.md` for workflow logic
2. Identify event-driven workflows (User Event scripts)
3. Understand scheduled automation processes
4. Trace state machine transitions

**Integration Mapping:**
1. Load `PRI_CONTAINER_TRACKING_INTEGRATION_ARCHITECTURE.md`
2. Identify NetSuite module dependencies
3. Understand Bundle 132118 critical dependency
4. Map standard record customizations

**Example Architecture Workflow:**
```
Question: How does container receiving work?
    ↓
1. Load Master Reference > User Workflows > "Receive Container"
2. Load Backend Processing > Item Receipt Processing
3. Trace: pri_itemrcpt_ss.js (beforeSubmit) → LC allocation → Queue entry
4. Follow: pri_itemrcpt_lcPerLnTemplate_sc.js (scheduled) → LC processing
5. Load Data Model > Container Record for validation context
```

### 4. Modification Planning

Plan system modifications systematically:

**Step 1: Assess Impact**
- Load Integration Architecture to understand dependencies
- Review Customization Analysis for existing modifications
- Check Backend Processing for affected workflows

**Step 2: Design Changes**
- Identify impacted custom records/fields
- Determine affected scripts (User Event, Scheduled, Client)
- Plan UI modifications (Suitelets, Client Scripts)

**Step 3: Plan Testing**
- Review existing test patterns
- Identify regression risks
- Plan sandbox testing approach

**Example Modification Workflow:**
```
Task: Add new field to Production PO Line
    ↓
1. Load Data Model > Production Management PO Line section
2. Review field list and business rules
3. Check Backend Processing > Production Management Lines
4. Identify affected scripts:
   - pri_cntProdMgmtLn_ss.js (User Event)
   - pri_cntProdMgmt_lib.js (Core Library)
   - pri_cntProdMgmt_cl.js (Client Script)
5. Load UI/UX Analysis > Production PO Management Form
6. Plan form customizations
7. Review Customization Analysis > Testing Requirements
```

### 5. Manual Remediation

Use diagnostic scripts for manual intervention:

**reset_stuck_queue.js**
- **Purpose:** Reset queue entries stuck in "Processing" status
- **When:** Queue processing frozen, scheduled scripts not progressing
- **Deploy:** As Suitelet (unrestricted)
- **Usage:** Select queue name → Reset entries stuck > 1 hour

**sync_container_dates.js**
- **Purpose:** Manually sync container ETD/ATA dates to TO/IF
- **When:** Date synchronization failed, manual correction needed
- **Deploy:** As Suitelet (unrestricted)
- **Usage:** Enter Container ID → Sync dates to TO and IF

**reset_ppo_line_status.js**
- **Purpose:** Reset Production PO Line from Locked to Available
- **When:** Line shows Locked but no PO exists (data corruption)
- **Deploy:** As Suitelet (admin-only)
- **WARNING:** Validate no linked PO before using
- **Usage:** Enter Line ID → Verify no PO → Reset status

**Deployment Instructions:**
1. Upload script to File Cabinet: `/SuiteScripts/Diagnostics/`
2. Create Script record (Suitelet type)
3. Create Deployment (set appropriate role restrictions)
4. Navigate to Suitelet URL for execution

See `scripts/README.md` for detailed deployment and usage instructions.

## Key System Components

### Production Purchase Order System

**Purpose:** Blanket PO emulation with sophisticated price locking

**Key Records:**
- `customrecord_pri_frgt_cnt_pm` - Production PO Header
- `customrecord_pri_frgt_cnt_pmln` - Production PO Line
- `customrecord_pri_frgt_cnt_iv` - Item Version

**Key Scripts:**
- `pri_cntProdMgmt_lib.js` - Core library (1,854 lines)
- `pri_cntProdPoGenerator_sl.js` - PO generation Suitelet
- `pri_cntProdMgmtLn_ss.js` - Line events

**Features:**
- JSON-based price locking mechanism (captures item group pricing)
- Item group support with member pricing
- Async quantity calculation via queue
- Time-based item version sourcing
- Status-based edit restrictions (Available/Locked)

**Common Issues:**
- Lines locked without PO: Use `reset_ppo_line_status.js`
- Item group receipt imbalance: Re-lock price on PPO line
- Quantity calculation slow: Check queue processing

### Container Logistics System

**Purpose:** Multi-modal freight tracking with automatic TO creation

**Key Records:**
- `customrecord_pri_frgt_cnt` - Container
- `customrecord_pri_frgt_cnt_vsl` - Vessel (parent)
- `customrecord_pri_frgt_cnt_carrier` - Carrier

**Key Scripts:**
- `pri_container_ss.js` - Container events
- `pri_CL_container.js` - Container UI
- `pri_trnfrord_ss.js` - Transfer order integration

**Features:**
- 6 status progression values (Origin → Destination)
- Automatic Transfer Order creation on button click
- 3-level date synchronization (Container → TO → IF)
- Bin management integration
- Field inheritance from parent vessel

**Common Issues:**
- Dates not syncing: Use `sync_container_dates.js`
- TO not created: Check container location field
- Status locked: Verify container not at origin for IR

### In-Transit Linking System

**Purpose:** Container distribution to multiple locations via junction table

**Key Record:**
- `customrecord_pri_frgt_cnt_ir_to_lnkr` - IR to TO Linker

**Key Scripts:**
- `pri_irToLinker_ss.js` - Linker events (cascade creation)
- `pri_irToLinker_lib.js` - Core library

**Features:**
- Single linker record creates TO + IF automatically
- Auto-fulfills Item Fulfillment
- Multi-container distribution tracking
- Validates IR at origin, container with location

**CRITICAL WARNING:**
- Linker deletion orphans TO and IF records (no rollback mechanism)
- Always backup or manually delete TO/IF before deleting linker
- No built-in transaction rollback on failure

**Common Issues:**
- Deletion orphans transactions: Manual cleanup required (no automated fix)
- Linker creation fails: Check IR at origin location, container has destination
- Multiple linkers: Allowed, each creates separate TO/IF

### Landed Cost System

**Purpose:** Advanced cost allocation with template-driven processing

**Key Records:**
- `customrecord_pri_frgt_cnt_lct` - LC Template
- `customrecord_pri_frgt_cnt_lctd` - LC Template Detail

**Key Scripts:**
- `pri_itemrcpt_lib.js` - Core library (4,221 lines - largest)
- `pri_itemrcpt_ss.js` - Item receipt events
- `pri_itemrcpt_lcPerLnTemplate_sc.js` - Scheduled processor

**Features:**
- 3 allocation methods:
  - Per Quantity: Fair distribution by units received
  - Flat Amount: Equal distribution across lines
  - Percentage: Value-based proportional allocation
- Queue-based processing for receipts > 10 lines
- Bin/serial/lot allocation support
- Transfer order special handling
- Workflow Action integration

**Common Issues:**
- LC not allocating: Check template exists, verify queue processing
- Allocation amounts wrong: Review template method and details
- Queue stuck: Use `reset_stuck_queue.js` for PRI_LC_TEMPLATE

## Common Issues Quick Reference

| Symptom | Likely Cause | Quick Action |
|---------|--------------|--------------|
| TO line dates not syncing | Hardcoded logic bypasses Setting 250 | Check Application Settings, use `sync_container_dates.js` |
| Field mappings not applying | Status gate or configuration error | Review Application Settings Catalog |
| PO lines locked unexpectedly | Status corruption or script error | Use `reset_ppo_line_status.js` |
| LC not allocating | Template missing or queue failed | Check template, re-queue |
| Container dates not syncing | TO not linked or script disabled | Use `sync_container_dates.js` |
| Queue stuck | Script error or governance issue | Use `reset_stuck_queue.js` |
| Item group imbalance error | Member mismatch or qty wrong | Re-lock price on PPO line |
| Linker deletion orphans TO/IF | No rollback mechanism | Manual cleanup required |
| Production PO generation fails | Data validation or permissions | Check execution logs, verify data |
| Container receiving fails | Status wrong or TO missing | Verify status = 7, TO linked |

**For detailed resolutions:** Load `PRI_CONTAINER_TRACKING_MASTER_REFERENCE.md` > Troubleshooting Matrix

## Twisted X Customizations

**Bundle 132118 - Field Mapping (MODIFIED):**
- **Line 103 null check fix:** Critical for EDI automation
- **Impact:** Must re-apply after each Bundle 132118 upgrade
- **File:** `PRI_FieldMapping.js`

**Bundle 168443 - RSM Framework (UNMODIFIED):**
- Used via plugin architecture (no modifications)
- `TX_RSM_Plugin.js` implements 12 custom SO validation rules
- Maintains full upgradability

**Custom Extensions:**
1. **BPA Contact Role Sync:** Automated AP email list management
2. **Optimized Field Mapping:** 70% performance improvement using SuiteQL
3. **EDI Amount Integration:** Automated 850 amount calculation via PRI UTIL
4. **RSM Custom Rules:** Credit, routing, territory validations

**Upgrade Strategy:**
- Bundle 132118: Re-apply field mapping fix after upgrade
- Bundle 168443: No modifications, direct upgrade
- Test customizations after each upgrade

**For detailed upgrade procedures:** Load `PRI_BUNDLE_CUSTOMIZATION_ANALYSIS.md` > Upgrade Strategy

## Best Practices

**When Debugging:**
1. Check script execution logs first (identify error type)
2. Verify queue entry status for async operations
3. Validate container/TO/IF linkages before manual intervention
4. Always test diagnostic scripts in Sandbox before production

**When Understanding:**
1. Start with Master Reference for overview
2. Use Quick Reference for fast lookups
3. Load specific references for deep-dives
4. Trace workflows from User Event → Queue → Scheduled

**When Modifying:**
1. Review existing customizations to avoid conflicts
2. Understand Bundle 132118 dependencies (Queue Manager required)
3. Test with item groups (complex pricing logic)
4. Follow existing code patterns (AMD modules, error handling)

**When Upgrading:**
1. Document current bundle versions before upgrade
2. Test Bundle 132118 upgrade with field mapping fix
3. Validate RSM plugin compatibility (should be stable)
4. Run regression tests on custom extensions (BPA, EDI)

## Architecture Quick Facts

- **Total Scripts:** 47 files across 6 script types
- **Code Volume:** ~20,835 lines of SuiteScript 2.1
- **Largest Library:** pri_itemrcpt_lib.js (4,221 lines)
- **Most Complex Module:** Production Management (price locking, item groups, versions)
- **Most Automated:** IR to TO Linker (3-level transaction cascade)
- **Critical Dependency:** Bundle 132118 Queue Manager (17+ scripts depend on it)
- **External Integrations:** Zero - Pure NetSuite architecture
- **Custom Records:** 10 types with 100+ custom fields
- **Script Deployments:** 35 active deployments

## Resources

### Reference Documentation (`references/`)

All comprehensive documentation organized by category:

**Configuration & Settings:**
- **Application Settings Architecture** (27KB) - Configuration system design, PRI_AS_Engine, SYNCSRCDEF
- **Application Settings Catalog** (20KB) - Complete catalog of all 23+ settings with JSON examples
- **Application Settings Field Mapping Analysis** (20KB) - Deep-dive on field mapping engine internals

**System Understanding:**
- **Master Reference** (76KB) - Start here for troubleshooting workflows and diagnostic guides
- **Backend Processing** (57KB) - Event-driven workflows, scheduled automation, business rules
- **Integration Architecture** (52KB) - Dependencies, NetSuite modules, security model
- **Data Model** (37KB) - Complete entity documentation, field mappings, business rules
- **UI/UX Analysis** (35KB) - User interface patterns, form customizations, workflows

**Customization & Operations:**
- **Customization Analysis** (31KB) - Twisted X modifications, upgrade strategies
- **Analysis Summary** (19KB) - Executive overview, risk assessment, recommendations
- **Quick Reference** (13KB) - Fast lookups for scripts, fields, error messages

**Usage:** Load relevant reference files based on task category. Use grep for targeted searches within large files.

### Diagnostic Scripts (`scripts/`)

Manual remediation tools deployable as Suitelets:

- **reset_stuck_queue.js** - Reset queue entries stuck in Processing status
- **sync_container_dates.js** - Manually sync container dates to TO/IF
- **reset_ppo_line_status.js** - Reset locked Production PO Line status
- **README.md** - Detailed deployment and usage instructions

**Usage:** Deploy scripts to `/SuiteScripts/Diagnostics/` and create Suitelet deployments. Always test in Sandbox first.

---

**Skill Version:** 1.1
**Last Updated:** 2025-11-12
**Analysis Confidence:** 95%+ (based on systematic code analysis)
**Documentation Size:** ~390KB across 11 reference files
**New in v1.1:** Application Settings configuration knowledge (23+ settings documented)
