"""Tests for new resource handlers: Tools, BuilderApis, McpServers, AsyncHelpers,
Notifications, OPA, TradingPartnerConnectors, EDI extensions."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


# ---------------------------------------------------------------------------
# Helper: build a minimal args namespace
# ---------------------------------------------------------------------------

def _args(**kwargs):
    ns = MagicMock()
    ns.env = None
    ns.format = "json"
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# ToolsAPI unit tests
# ---------------------------------------------------------------------------

class TestToolsAPI:
    def _make_client(self):
        from celigo_api import ToolsAPI, CeligoClient
        client = MagicMock(spec=CeligoClient)
        api = ToolsAPI(client)
        return api, client

    def test_list(self):
        api, client = self._make_client()
        client.get.return_value = [{"_id": "t1"}]
        assert api.list() == [{"_id": "t1"}]
        client.get.assert_called_once_with("/tools")

    def test_invoke(self):
        api, client = self._make_client()
        client.post.return_value = {"result": "ok"}
        result = api.invoke("t1", {"input": "x"})
        assert result == {"result": "ok"}
        client.post.assert_called_once_with("/tools/t1/invoke", {"input": "x"})

    def test_dependencies(self):
        api, client = self._make_client()
        client.get.return_value = {"flows": []}
        api.dependencies("t1")
        client.get.assert_called_once_with("/tools/t1/dependencies")

    def test_update_fetch_merge_put(self):
        """update() must fetch current, merge, then PUT (full-replace discipline)."""
        from celigo_api import ToolsAPI, CeligoClient
        client = MagicMock(spec=CeligoClient)
        api = ToolsAPI(client)

        current = {"_id": "t1", "name": "old", "description": "d", "lastModified": "ts"}
        client.get.return_value = current

        api.update("t1", {"name": "new"})
        # PUT must have been called with the merged payload (not just the partial)
        put_call = client.put.call_args
        assert put_call is not None
        body = put_call[0][1]
        assert body["name"] == "new"
        assert body["description"] == "d"
        assert "_id" not in body  # readonly stripped


# ---------------------------------------------------------------------------
# McpServersAPI lifecycle tests
# ---------------------------------------------------------------------------

class TestMcpServersAPI:
    def _make(self):
        from celigo_api import McpServersAPI, CeligoClient
        client = MagicMock(spec=CeligoClient)
        return McpServersAPI(client), client

    def test_start_is_post(self):
        api, client = self._make()
        client.post.return_value = {"status": "starting"}
        api.start("s1")
        client.post.assert_called_once_with("/mcpServers/s1/start")

    def test_status_is_get(self):
        api, client = self._make()
        client.get.return_value = {"status": "running"}
        result = api.status("s1")
        assert result == {"status": "running"}
        client.get.assert_called_once_with("/mcpServers/s1/status")


# ---------------------------------------------------------------------------
# AsyncHelpersAPI wait() tests
# ---------------------------------------------------------------------------

class TestAsyncHelpersWait:
    def _make(self):
        from celigo_api import AsyncHelpersAPI, CeligoClient
        client = MagicMock(spec=CeligoClient)
        return AsyncHelpersAPI(client), client

    def test_wait_returns_result_on_done(self):
        api, client = self._make()
        client.post.return_value = {"_id": "job1"}
        # First poll → running; second poll → done
        client.get.side_effect = [
            {"status": "running"},
            {"status": "done"},
            {"data": "final"},
        ]
        result = api.wait("myOp", timeout=10, interval=0)
        assert result == {"data": "final"}

    def test_wait_raises_on_timeout(self):
        api, client = self._make()
        client.post.return_value = {"_id": "job1"}
        client.get.return_value = {"status": "running"}
        with pytest.raises(TimeoutError):
            api.wait("myOp", timeout=1, interval=0)

    def test_wait_returns_error_on_failed(self):
        api, client = self._make()
        client.post.return_value = {"_id": "job1"}
        client.get.return_value = {"status": "failed", "reason": "oops"}
        result = api.wait("myOp", timeout=10, interval=0)
        assert result["error"] is True


# ---------------------------------------------------------------------------
# OpaAPI tests
# ---------------------------------------------------------------------------

class TestOpaAPI:
    def _make(self):
        from celigo_api import OpaAPI, CeligoClient
        client = MagicMock(spec=CeligoClient)
        return OpaAPI(client), client

    def test_status_endpoint(self):
        api, client = self._make()
        client.get.return_value = {"connected": True}
        api.status("a1")
        client.get.assert_called_once_with("/agents/a1/status")

    def test_restart_endpoint(self):
        api, client = self._make()
        client.post.return_value = {"queued": True}
        api.restart("a1")
        client.post.assert_called_once_with("/agents/a1/restart")


# ---------------------------------------------------------------------------
# EDI Profiles: fileType immutability guard
# ---------------------------------------------------------------------------

class TestEdiFileTypeGuard:
    @patch("celigo_api.CeligoClient")
    def test_update_rejects_fileType_mutation(self, MockClient):
        from celigo_api import cmd_edi
        args = _args(action="update", id="ep1",
                     data='{"fileType": "X12", "name": "new"}', file=None)
        with pytest.raises(SystemExit) as exc:
            cmd_edi(args)
        assert exc.value.code == 1

    @patch("celigo_api.CeligoClient")
    def test_update_allows_non_immutable_fields(self, MockClient):
        from celigo_api import cmd_edi, EDIAPI
        mock_instance = MockClient.return_value
        mock_instance.get.return_value = {
            "_id": "ep1", "name": "old", "fileType": "X12", "lastModified": "ts"
        }
        mock_instance.put.return_value = {"_id": "ep1", "name": "new", "fileType": "X12"}

        args = _args(action="update", id="ep1", data='{"name": "new"}', file=None)
        cmd_edi(args)  # should NOT raise
        put_body = mock_instance.put.call_args[0][1]
        assert put_body["fileType"] == "X12"  # preserved
        assert put_body["name"] == "new"


# ---------------------------------------------------------------------------
# File Definitions: EDI format validation
# ---------------------------------------------------------------------------

class TestFileDefinitionsEdiValidation:
    @patch("celigo_api.CeligoClient")
    def test_create_x12_requires_documentType(self, MockClient):
        from celigo_api import cmd_filedefinitions
        mock_instance = MockClient.return_value
        args = _args(action="create",
                     data='{"format":"x12","globalId":"GID1"}',
                     file=None, schema_version=None)
        with pytest.raises(SystemExit) as exc:
            cmd_filedefinitions(args)
        assert exc.value.code == 1

    @patch("celigo_api.CeligoClient")
    def test_create_x12_requires_globalId(self, MockClient):
        from celigo_api import cmd_filedefinitions
        mock_instance = MockClient.return_value
        args = _args(action="create",
                     data='{"format":"x12","documentType":"850"}',
                     file=None, schema_version=None)
        with pytest.raises(SystemExit) as exc:
            cmd_filedefinitions(args)
        assert exc.value.code == 1

    @patch("celigo_api.CeligoClient")
    def test_create_delimited_no_edi_fields_required(self, MockClient):
        from celigo_api import cmd_filedefinitions
        mock_instance = MockClient.return_value
        mock_instance.post.return_value = {"_id": "fd1"}
        args = _args(action="create",
                     data='{"format":"delimited","name":"test"}',
                     file=None, schema_version=None)
        cmd_filedefinitions(args)  # should NOT raise
        mock_instance.post.assert_called_once()
