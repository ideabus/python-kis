import os
import stat
from unittest.mock import MagicMock, patch

import pytest

from pykis import PyKis
from pykis.client.exceptions import KisHTTPError
from pykis.utils.workspace import ensure_private_dir, write_private_text

APPKEY = "A" * 36
SECRETKEY = "B" * 180


def make_kis(**kwargs) -> PyKis:
    kis = PyKis(
        id="id",
        account="00000000-01",
        appkey=APPKEY,
        secretkey=SECRETKEY,
        use_websocket=False,
        **kwargs,
    )
    kis._token = MagicMock()
    return kis


def response(ok: bool, code: str | None = None) -> MagicMock:
    r = MagicMock()
    r.ok = ok
    r.status_code = 200 if ok else 500
    r.reason = "reason"
    r.text = "text"
    r.json.return_value = {"msg_cd": code}
    r.request.headers = {}
    r.request.body = None
    r.request.url = "https://example.com/path"
    r.request.method = "POST"
    return r


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("pykis.kis.sleep") as sleep:
        yield sleep


def test_request_passes_timeout():
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(return_value=response(True))

    kis.request("/x", method="POST", auth=False)

    assert session.request.call_args.kwargs["timeout"] is not None


def test_token_expired_retries_then_succeeds():
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(side_effect=[response(False, "EGW00123"), response(True)])

    kis.request("/x", method="POST", auth=False)

    assert session.request.call_count == 2


def test_token_expired_gives_up():
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(return_value=response(False, "EGW00123"))

    with pytest.raises(KisHTTPError):
        kis.request("/x", auth=False)

    assert session.request.call_count == 3  # 최초 1회 + 재시도 2회


def test_rate_limit_backs_off_then_succeeds(no_sleep):
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(side_effect=[response(False, "EGW00201")] * 6 + [response(True)])

    kis.request("/x", auth=False)

    assert session.request.call_count == 7
    delays = [c.args[0] for c in no_sleep.call_args_list]
    assert delays == sorted(delays) and max(delays) <= 1.0


def test_rate_limit_gives_up_after_max_wait():
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(return_value=response(False, "EGW00201"))

    with pytest.raises(KisHTTPError):
        kis.request("/x", auth=False)


def test_other_error_not_retried():
    kis = make_kis()
    session = kis._sessions["real"]
    session.request = MagicMock(return_value=response(False, "OTHER"))

    with pytest.raises(KisHTTPError):
        kis.request("/x", auth=False)

    assert session.request.call_count == 1


def test_virtual_via_keyword_arguments():
    kis = make_kis(virtual_id="vid", virtual_appkey=APPKEY, virtual_secretkey=SECRETKEY)

    assert kis.virtual
    assert kis.virtual_appkey.id == "vid"


def test_virtual_id_falls_back_to_id():
    kis = make_kis(virtual_appkey=APPKEY, virtual_secretkey=SECRETKEY)

    assert kis.virtual_appkey.id == "id"


def test_virtual_secretkey_required():
    with pytest.raises(ValueError, match="virtual_secretkey"):
        make_kis(virtual_appkey=APPKEY)


@pytest.mark.skipif(os.name == "nt", reason="POSIX 권한")
def test_write_private_text_permissions_and_overwrite(tmp_path):
    path = tmp_path / "secret.json"
    path.write_text("old")
    path.chmod(0o644)

    write_private_text(path, "new")

    assert path.read_text() == "new"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == ["secret.json"]


def test_write_private_text_failure_keeps_original(tmp_path):
    path = tmp_path / "secret.json"
    path.write_text("old")

    with patch("pykis.utils.workspace.os.replace", side_effect=OSError("boom")):
        with pytest.raises(OSError):
            write_private_text(path, "new")

    assert path.read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["secret.json"]


def test_write_private_text_does_not_close_foreign_fd(tmp_path):
    """쓰기 실패 시 이미 닫힌 fd를 다시 close하지 않아야 합니다."""
    path = tmp_path / "secret.json"

    with patch("pykis.utils.workspace.os.close") as close:
        with patch("pykis.utils.workspace.os.fdopen", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                write_private_text(path, "x")

    close.assert_not_called()


@pytest.mark.skipif(os.name == "nt", reason="POSIX 권한")
def test_ensure_private_dir_only_restricts_new_dirs(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    existing.chmod(0o755)

    target = ensure_private_dir(existing / "a" / "b")

    assert stat.S_IMODE(existing.stat().st_mode) == 0o755
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
