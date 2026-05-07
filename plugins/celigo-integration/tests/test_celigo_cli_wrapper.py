"""Tests for celigo_cli_wrapper.py"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from celigo_cli_wrapper import is_available, run, version


class TestRunHappy:
    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_returns_parsed_json(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='[{"_id": "abc"}]', stderr=""
        )
        result = run("integrations list")
        assert result == [{"_id": "abc"}]

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_json_output_flag_added(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        run("tools list")
        called_argv = mock_run.call_args[0][0]
        assert "--output" in called_argv
        assert "json" in called_argv

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_env_name_passed_as_flag(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        run("integrations list", env_name="sandbox")
        called_argv = mock_run.call_args[0][0]
        assert "--environment" in called_argv
        assert "sandbox" in called_argv

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_raw_string_when_json_output_false(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="some text", stderr="")
        result = run("--version", json_output=False)
        assert result == "some text"

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_empty_stdout_returns_empty_dict(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = run("tools list")
        assert result == {}


class TestRunErrors:
    @patch("celigo_cli_wrapper.shutil.which", return_value=None)
    def test_cli_not_installed_raises(self, mock_which):
        with pytest.raises(FileNotFoundError):
            run("tools list")

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_non_zero_exit_raises(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="resource not found"
        )
        with pytest.raises(subprocess.CalledProcessError):
            run("tools get nonexistent")

    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    @patch("celigo_cli_wrapper.subprocess.run")
    def test_non_json_stdout_degrades_gracefully(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Usage: celigo [options]", stderr=""
        )
        result = run("--help")
        assert isinstance(result, str)
        assert "Usage" in result


class TestHelpers:
    @patch("celigo_cli_wrapper.shutil.which", return_value="/usr/bin/celigo")
    def test_is_available_true_when_binary_found(self, mock_which):
        assert is_available() is True

    @patch("celigo_cli_wrapper.shutil.which", return_value=None)
    def test_is_available_false_when_missing(self, mock_which):
        assert is_available() is False
