import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from labshare import cli, hotspot, ui
from labshare.hotspot.base import HotspotError


class UiTests(unittest.TestCase):
    def feed(self, lines):
        it = iter(lines)

        def fake_input(prompt=""):
            try:
                return next(it)
            except StopIteration:
                raise EOFError

        return mock.patch("builtins.input", fake_input)

    def test_multiline_stops_at_end_marker(self):
        with self.feed(["a", "  b", ".END", "ignored"]), redirect_stdout(io.StringIO()):
            self.assertEqual(ui.read_multiline(), "a\n  b")

    def test_multiline_eof_finishes(self):
        with self.feed(["only"]), redirect_stdout(io.StringIO()):
            self.assertEqual(ui.read_multiline(), "only")

    def test_preview_truncates(self):
        self.assertEqual(ui.preview({"body": "\n\nhello"}), "hello")
        self.assertTrue(ui.preview({"body": "x" * 100}).endswith("..."))

    def test_save_message_uses_received_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                with self.feed([""]), redirect_stdout(io.StringIO()):
                    ui._save_message({"id": 7, "filename": "sol.py", "body": "x = 1\n"})
                with open(os.path.join("received", "sol.py"), encoding="utf-8", newline="") as fh:
                    self.assertEqual(fh.read(), "x = 1\n")
            finally:
                os.chdir(old)


class CliTests(unittest.TestCase):
    def test_default_command_is_client(self):
        fake = mock.Mock(return_value=0)
        with mock.patch.dict(cli.HANDLERS, {"client": fake}):
            cli.main(["--name", "x", "--host", "1.2.3.4"])
        args = fake.call_args[0][0]
        self.assertEqual((args.name, args.host), ("x", "1.2.3.4"))

    def test_info_runs(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["info"]), 0)
        self.assertIn("LabShare", out.getvalue())

    def test_hotspot_password_validation(self):
        with self.assertRaises(HotspotError):
            from labshare.hotspot.base import check_password
            check_password("short")

    def test_hotspot_unsupported_platform(self):
        with mock.patch("sys.platform", "darwin"):
            with self.assertRaises(HotspotError):
                hotspot.status()


if __name__ == "__main__":
    unittest.main()
