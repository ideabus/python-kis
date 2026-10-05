import os
import stat
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from pykis.client.auth import KisAuth
from pykis.client.cache import KisCacheStorage
from pykis.utils.rate_limit import RateLimiter


class TestKisCacheStorage(unittest.TestCase):
    def test_overwrite_without_expire_clears_old_expiry(self):
        cache = KisCacheStorage()
        cache.set("k", 1, datetime.now() - timedelta(seconds=1))
        cache.set("k", 2)

        self.assertEqual(cache.get("k", int), 2)

    def test_expired_entry_removed_completely(self):
        cache = KisCacheStorage()
        cache.set("k", 1, -1)

        self.assertIsNone(cache.get("k", int))
        self.assertNotIn("k", cache._expire)


class TestRateLimiter(unittest.TestCase):
    def test_non_blocking(self):
        limiter = RateLimiter(2, 10)

        self.assertTrue(limiter.acquire(blocking=False))
        self.assertTrue(limiter.acquire(blocking=False))
        self.assertFalse(limiter.acquire(blocking=False))

    def test_blocking_waits_for_next_period(self):
        limiter = RateLimiter(1, 0.2)
        limiter.acquire()
        start = time.monotonic()
        limiter.acquire()

        self.assertGreaterEqual(time.monotonic() - start, 0.15)


class TestPrivateFiles(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX 권한 검사")
    def test_auth_saved_with_owner_only_permission(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "secret.json"
            auth = KisAuth(id="id", appkey="a", secretkey="s", account="00000000-01", virtual=False)
            auth.save(path)

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(KisAuth.load(path), auth)


if __name__ == "__main__":
    unittest.main()
