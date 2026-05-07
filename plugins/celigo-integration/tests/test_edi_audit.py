"""Tests for edi_audit.py"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestParseHelpers:
    def test_parse_since_relative_hours(self):
        from edi_audit import _parse_since, _now_utc
        from datetime import timedelta
        result = _parse_since("6h")
        expected = _now_utc() - timedelta(hours=6)
        diff = abs((result - expected).total_seconds())
        assert diff < 5  # within 5s

    def test_parse_since_relative_days(self):
        from edi_audit import _parse_since, _now_utc
        from datetime import timedelta
        result = _parse_since("7d")
        expected = _now_utc() - timedelta(days=7)
        diff = abs((result - expected).total_seconds())
        assert diff < 5

    def test_parse_since_iso(self):
        from edi_audit import _parse_since
        result = _parse_since("2026-01-01T00:00:00Z")
        assert result.year == 2026

    def test_extract_po_from_externalid_valid(self):
        from edi_audit import _extract_po_from_externalid
        assert _extract_po_from_externalid("HIST_PO12345_ACME_00") == "PO12345"

    def test_extract_po_from_externalid_invalid(self):
        from edi_audit import _extract_po_from_externalid
        assert _extract_po_from_externalid("NOTAHISTID") is None

    def test_extract_po_from_externalid_none(self):
        from edi_audit import _extract_po_from_externalid
        assert _extract_po_from_externalid(None) is None


class TestEdiIntegrationParsing:
    def test_staging_integrations_skipped(self):
        from edi_audit import _STAGING_RE, _EDI_FLOW_RE
        name = "ACME Corp - EDI 850 IB (12/31/2025)"
        assert _STAGING_RE.search(name)

    def test_non_staging_inbound_matched(self):
        from edi_audit import _EDI_FLOW_RE
        name = "ACME Corp - EDI 850 IB"
        m = _EDI_FLOW_RE.match(name)
        assert m is not None
        assert m.group("partner") == "ACME Corp"
        assert m.group("doc_type") == "850"
        assert m.group("dir").upper() == "IB"

    def test_outbound_matched(self):
        from edi_audit import _EDI_FLOW_RE
        name = "ACME Corp - EDI 810 OB"
        m = _EDI_FLOW_RE.match(name)
        assert m is not None
        assert m.group("dir").upper() == "OB"

    def test_non_edi_integration_not_matched(self):
        from edi_audit import _EDI_FLOW_RE
        name = "Shopify - Order Import"
        assert _EDI_FLOW_RE.match(name) is None


class TestReconcileInbound:
    def test_clean_match_no_mismatches(self):
        from edi_audit import _reconcile_inbound
        jobs = [{"status": "completed"}, {"status": "completed"}]
        ns_rows = [
            {"id": "1", "externalid": "HIST_PO001_ACME_00", "status": "2",
             "transaction_id": "SO123", "created": "2026-01-01"},
            {"id": "2", "externalid": "HIST_PO002_ACME_00", "status": "2",
             "transaction_id": "SO124", "created": "2026-01-01"},
        ]
        result = _reconcile_inbound(jobs, ns_rows, "ACME", "850")
        assert result == []

    def test_ns_status_error_flagged(self):
        from edi_audit import _reconcile_inbound
        jobs = [{"status": "completed"}]
        ns_rows = [
            {"id": "1", "externalid": "HIST_PO001_ACME_00", "status": "6",
             "transaction_id": None, "created": "2026-01-01"},
        ]
        result = _reconcile_inbound(jobs, ns_rows, "ACME", "850")
        buckets = [m["bucket"] for m in result]
        assert "ns_status_error" in buckets

    def test_850_missing_transaction_flagged(self):
        from edi_audit import _reconcile_inbound
        jobs = [{"status": "completed"}]
        ns_rows = [
            {"id": "1", "externalid": "HIST_PO001_ACME_00", "status": "2",
             "transaction_id": None, "created": "2026-01-01"},
        ]
        result = _reconcile_inbound(jobs, ns_rows, "ACME", "850")
        types = [m["type"] for m in result]
        assert "pos_without_order" in types

    def test_celigo_success_ns_missing_flagged(self):
        from edi_audit import _reconcile_inbound
        jobs = [{"status": "completed"}, {"status": "completed"}]
        ns_rows = [
            {"id": "1", "externalid": "HIST_PO001_ACME_00", "status": "2",
             "transaction_id": "SO1", "created": "2026-01-01"},
        ]
        result = _reconcile_inbound(jobs, ns_rows, "ACME", "850")
        buckets = [m["bucket"] for m in result]
        assert "celigo_success_ns_missing" in buckets


class TestReconcileOutbound:
    def test_ns_sent_celigo_missing_flagged(self):
        from edi_audit import _reconcile_outbound
        ns_rows = [
            {"id": "1", "externalid": "HIST_INV001_ACME_00", "status": "2",
             "transaction_id": "INV1", "created": "2026-01-01"},
        ]
        result = _reconcile_outbound(ns_rows, celigo_jobs=[], partner="ACME",
                                     doc_type="810")
        assert any(m["bucket"] == "ns_sent_celigo_missing" for m in result)

    def test_clean_outbound_no_mismatches(self):
        from edi_audit import _reconcile_outbound
        ns_rows = [{"id": "1", "status": "2"}]
        celigo_jobs = [{"status": "completed"}]
        result = _reconcile_outbound(ns_rows, celigo_jobs, "ACME", "810")
        assert result == []


class TestRunAuditIntegration:
    """Integration-level tests using mocked Celigo + NS calls."""

    @patch("edi_audit._get_jobs_for_integration")
    @patch("edi_audit._ns_edi_history_inbound")
    @patch("edi_audit._get_edi_integrations")
    @patch("edi_audit._get_celigo_creds")
    def test_full_audit_clean(self, mock_creds, mock_integrations, mock_ns, mock_jobs):
        from edi_audit import run_audit
        mock_creds.return_value = ("https://api.integrator.io/v1", "testkey")
        mock_integrations.return_value = [{
            "_id": "int1", "name": "ACME - EDI 850 IB",
            "partner": "ACME", "doc_type": "850", "direction": "IB"
        }]
        mock_jobs.return_value = [{"status": "completed"}]
        mock_ns.return_value = [{
            "id": "1", "externalid": "HIST_PO1_ACME_00",
            "status": "2", "transaction_id": "SO1", "created": "2026-01-01"
        }]

        result = run_audit("24h", None, "inbound", None, None)
        assert result["total_mismatches"] == 0

    @patch("edi_audit._get_jobs_for_integration")
    @patch("edi_audit._ns_edi_history_inbound")
    @patch("edi_audit._get_edi_integrations")
    @patch("edi_audit._get_celigo_creds")
    def test_full_audit_detects_mismatch(self, mock_creds, mock_integrations, mock_ns, mock_jobs):
        from edi_audit import run_audit
        mock_creds.return_value = ("https://api.integrator.io/v1", "testkey")
        mock_integrations.return_value = [{
            "_id": "int1", "name": "ACME - EDI 850 IB",
            "partner": "ACME", "doc_type": "850", "direction": "IB"
        }]
        mock_jobs.return_value = [{"status": "completed"}, {"status": "completed"}]
        mock_ns.return_value = []  # no NS records → mismatch

        result = run_audit("24h", None, "inbound", None, None)
        assert result["total_mismatches"] > 0

    @patch("edi_audit._get_celigo_creds")
    @patch("edi_audit._get_edi_integrations")
    def test_partner_filter_applied(self, mock_integrations, mock_creds):
        from edi_audit import run_audit
        mock_creds.return_value = ("https://api.integrator.io/v1", "testkey")
        mock_integrations.return_value = []  # filter removes everything

        result = run_audit("24h", None, "both", "UNKNOWN_PARTNER", None)
        assert result["integrations_scanned"] == 0
