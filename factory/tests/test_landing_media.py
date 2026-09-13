"""Bounded child lifetime tests; no complex PDF input or real model calls."""

import selectors
import subprocess
import sys
import unittest
from unittest.mock import patch

from adaptive_factory import landing_media


class PdfChildLifetimeTests(unittest.TestCase):
    def test_successful_child_exchange_returns_text_and_closes_pipes(self):
        real_popen = subprocess.Popen
        children = []

        def dispose(process):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

        def spawn(*args, **kwargs):
            process = real_popen(
                (sys.executable, "-c", "import sys,json; sys.stdin.buffer.read(); "
                 "print(json.dumps({'schema_version':1,'text':'A bounded PDF brief'}))"),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, close_fds=True,
            )
            children.append(process)
            self.addCleanup(dispose, process)
            return process

        with patch.object(landing_media.subprocess, "Popen", side_effect=spawn):
            self.assertEqual("A bounded PDF brief", landing_media.extract_pdf_text(b"%PDF-1.7\nsynthetic\n%%EOF"))
        self.assertEqual(0, children[0].poll())
        self.assertTrue(all(stream.closed for stream in
                            (children[0].stdin, children[0].stdout, children[0].stderr)))

    def test_selector_failures_terminate_reap_child_and_close_every_pipe(self):
        real_popen = subprocess.Popen
        real_selector = selectors.DefaultSelector
        for stage in ("construct", "register", "close"):
            with self.subTest(stage=stage):
                children = []

                def dispose(process):
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    for stream in (process.stdin, process.stdout, process.stderr):
                        stream.close()

                def spawn(*args, **kwargs):
                    process = real_popen(
                        (sys.executable, "-c", "import time; time.sleep(30)"),
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        start_new_session=True, close_fds=True,
                    )
                    children.append(process)
                    self.addCleanup(dispose, process)
                    return process

                class FailingSelector:
                    def __init__(self):
                        if stage == "construct":
                            raise OSError("selector construction")
                        self.inner = real_selector()

                    def register(self, *args):
                        if stage == "register":
                            raise OSError("selector registration")
                        return self.inner.register(*args)

                    def get_map(self):
                        return self.inner.get_map()

                    def select(self, timeout):
                        raise OSError("selector selection")

                    def close(self):
                        self.inner.close()
                        if stage == "close":
                            raise OSError("selector close")

                with patch.object(landing_media.subprocess, "Popen", side_effect=spawn), patch.object(
                    landing_media.selectors, "DefaultSelector", FailingSelector,
                ):
                    with self.assertRaises(OSError):
                        landing_media.extract_pdf_text(b"%PDF-1.7\nsynthetic\n%%EOF")
                self.assertEqual(1, len(children))
                self.assertIsNotNone(children[0].poll(), "PDF child survived the failure")
                self.assertTrue(all(stream.closed for stream in
                                    (children[0].stdin, children[0].stdout, children[0].stderr)))


if __name__ == "__main__":
    unittest.main()
