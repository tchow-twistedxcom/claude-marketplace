# Threat API Reference

Two capability areas: Threat Assessment requests (`ThreatAssessment.Read.All`, always available) and
Microsoft Defender Threat Intelligence (`ThreatIntelligence.Read.All`, license-gated). Both are
Graph v1.0 and support app-only auth.

## Endpoints

| Operation | Method | Endpoint | Permission | Notes |
|-----------|--------|----------|------------|-------|
| List threat assessments | GET | `/informationProtection/threatAssessmentRequests` | `ThreatAssessment.Read.All` | available |
| Get assessment | GET | `/informationProtection/threatAssessmentRequests/{id}` | `ThreatAssessment.Read.All` | available |
| Assessment results | GET | `/informationProtection/threatAssessmentRequests/{id}/results` | `ThreatAssessment.Read.All` | available |
| MDTI articles | GET | `/security/threatIntelligence/articles` | `ThreatIntelligence.Read.All` | license-gated |
| MDTI host | GET | `/security/threatIntelligence/hosts/{id}` | `ThreatIntelligence.Read.All` | license-gated |
| MDTI intel profiles | GET | `/security/threatIntelligence/intelProfiles` | `ThreatIntelligence.Read.All` | license-gated |
| MDTI vulnerability | GET | `/security/threatIntelligence/vulnerabilities/{cve}` | `ThreatIntelligence.Read.All` | license-gated |

## CLI Commands

```bash
# Threat assessment requests (submitted email/url/file/mail assessments)
python3 azure_ad_api.py threat assessments
python3 azure_ad_api.py threat assessment REQUEST_ID
python3 azure_ad_api.py threat assessment-results REQUEST_ID

# Microsoft Defender Threat Intelligence (returns an "unavailable" message if unlicensed)
python3 azure_ad_api.py threat intel-articles --top 20
python3 azure_ad_api.py threat intel-host example.com
python3 azure_ad_api.py threat intel-profiles --top 20
python3 azure_ad_api.py threat intel-vulnerability CVE-2024-12345
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `azure_ad_threat_assessments` | List submitted threat assessment requests |
| `azure_ad_threat_assessment` | Get one assessment request |
| `azure_ad_threat_assessment_results` | Get the result detail for an assessment |
| `azure_ad_ti_articles` | MDTI threat articles (license-gated) |
| `azure_ad_ti_host` | MDTI host reputation/enrichment (license-gated) |
| `azure_ad_ti_profiles` | MDTI intel profiles (license-gated) |
| `azure_ad_ti_vulnerability` | MDTI vulnerability detail by CVE (license-gated) |

## Caveats

- **Threat assessment** read uses the `.Read.All` application permission and allows GET. The
  collection contains only assessments that have been **submitted** (typically by admins or transport
  rules), so it may be empty. It is not a passive threat feed.
- **Microsoft Defender Threat Intelligence** (`/security/threatIntelligence/*`) is GA on v1.0 and the
  app holds `ThreatIntelligence.Read.All`, but the API is gated behind a separate **MDTI premium plus
  API add-on license** on the tenant. Without that license every call returns a Forbidden/license
  error regardless of token. The CLI and MCP tools catch this and return a clear "unavailable,
  requires MDTI license" message rather than crashing. Confirm licensing before relying on these.
- **`ThreatIndicators.Read.All` is orphaned.** Its only endpoint, `/security/tiIndicators`, is beta
  and was deprecated and removed (around April 2026). No operation is built on it. Recommend removing
  this permission from the app registration (an admin action requiring human sign-off, not performed
  by this skill).
