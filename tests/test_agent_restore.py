"""
Tests pour la récupération et l'application des restaurations en attente
côté agent (agent/api_client.py, agent/cli.py::_apply_pending_restores).
"""
import zipfile
from unittest.mock import MagicMock, patch

from agent.api_client import SaveOSAPIClient
from agent.cli import _apply_pending_restores


# --- SaveOSAPIClient : nouvelles méthodes ---

@patch('requests.Session.get')
def test_list_pending_restores_success(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [{"id": 1}])

    client = SaveOSAPIClient("https://test.api", "test-token")
    result = client.list_pending_restores()

    assert result["success"] is True
    assert result["data"] == [{"id": 1}]


@patch('requests.Session.get')
def test_download_restore_package_writes_file(mock_get, tmp_path):
    mock_response = MagicMock(status_code=200)
    mock_response.iter_content.return_value = [b"PK", b"\x03\x04content"]
    mock_get.return_value = mock_response

    client = SaveOSAPIClient("https://test.api", "test-token")
    dest = str(tmp_path / "out.zip")

    result = client.download_restore_package(42, dest)

    assert result["success"] is True
    with open(dest, "rb") as f:
        assert f.read() == b"PK\x03\x04content"


@patch('requests.Session.get')
def test_download_restore_package_http_error(mock_get, tmp_path):
    mock_get.return_value = MagicMock(status_code=409, text="not ready")

    client = SaveOSAPIClient("https://test.api", "test-token")
    result = client.download_restore_package(42, str(tmp_path / "out.zip"))

    assert result["success"] is False
    assert "409" in result["error"]


@patch('requests.Session.post')
def test_report_job_status_success(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"id": 1, "status": "completed"})

    client = SaveOSAPIClient("https://test.api", "test-token")
    result = client.report_job_status(1, "completed")

    assert result["success"] is True
    args, kwargs = mock_post.call_args
    assert kwargs["json"] == {"status": "completed"}


# --- _apply_pending_restores ---

def test_apply_pending_restores_extracts_and_reports_completed(tmp_path):
    restore_dir = tmp_path / "restore_target"
    zip_source = tmp_path / "source.zip"
    with zipfile.ZipFile(zip_source, "w") as zf:
        zf.writestr("docs/a.txt", "hello")

    client = MagicMock()
    client.list_pending_restores.return_value = {
        "success": True,
        "data": [{"id": 1, "config": {"restore_path": str(restore_dir)}}],
    }

    def fake_download(job_id, dest_path):
        with open(zip_source, "rb") as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
        return {"success": True, "data": {"path": dest_path}}

    client.download_restore_package.side_effect = fake_download

    _apply_pending_restores(client)

    assert (restore_dir / "docs" / "a.txt").read_text() == "hello"
    client.report_job_status.assert_called_once_with(1, "completed")


def test_apply_pending_restores_reports_failed_on_missing_restore_path():
    client = MagicMock()
    client.list_pending_restores.return_value = {
        "success": True,
        "data": [{"id": 2, "config": {}}],
    }

    _apply_pending_restores(client)

    client.report_job_status.assert_called_once()
    args, _ = client.report_job_status.call_args
    assert args[0] == 2
    assert args[1] == "failed"
    client.download_restore_package.assert_not_called()


def test_apply_pending_restores_reports_failed_on_download_error(tmp_path):
    client = MagicMock()
    client.list_pending_restores.return_value = {
        "success": True,
        "data": [{"id": 3, "config": {"restore_path": str(tmp_path / "out")}}],
    }
    client.download_restore_package.return_value = {"success": False, "error": "HTTP 500"}

    _apply_pending_restores(client)

    client.report_job_status.assert_called_once_with(3, "failed", "HTTP 500")


def test_apply_pending_restores_noop_when_list_fails(capsys):
    client = MagicMock()
    client.list_pending_restores.return_value = {"success": False, "error": "boom"}

    _apply_pending_restores(client)

    client.download_restore_package.assert_not_called()
    client.report_job_status.assert_not_called()
