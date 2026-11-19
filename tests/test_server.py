import os
import tempfile
import threading
import unittest

from labshare.client import LabShareClient, LabShareError
from labshare.config import MAX_MESSAGE_BYTES
from labshare.server import LabShareServer


class ServerTests(unittest.TestCase):
    token = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = LabShareServer("127.0.0.1", 0, os.path.join(self.tmp.name, "t.db"), self.token)
        self.server.start()
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.clients = []

    def tearDown(self):
        for c in self.clients:
            c.close()
        self.server.shutdown()
        self.tmp.cleanup()

    def client(self, name, token=None):
        c = LabShareClient(name, "127.0.0.1", self.server.port, token)
        c.connect()
        self.clients.append(c)
        return c

    def test_send_to_online_user_and_mark_read(self):
        alice, bob = self.client("alice"), self.client("bob")
        reply = alice.send("bob", "print('hi')\nprint('there')", "code", "hello.py")
        self.assertTrue(reply["recipient_online"])
        messages = bob.inbox()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["body"], "print('hi')\nprint('there')")  # newlines survive
        self.assertEqual(messages[0]["filename"], "hello.py")
        self.assertEqual(bob.unread_count(), 1)
        bob.mark_read(messages[0]["id"])
        self.assertEqual(bob.inbox(), [])

    def test_offline_user_receives_on_reconnect(self):
        alice, bob = self.client("alice"), self.client("bob")
        bob.close()
        reply = alice.send("BOB", "while you were away", "text")
        self.assertFalse(reply["recipient_online"])
        bob2 = self.client("bob")
        self.assertEqual(bob2.unread, 1)
        self.assertEqual(bob2.inbox()[0]["body"], "while you were away")

    def test_user_list_shows_online_state(self):
        alice, bob = self.client("alice"), self.client("bob")
        bob.close()
        import time
        for _ in range(50):  # wait for the host to notice the disconnect
            states = {u["username"]: u["online"] for u in alice.list_users()}
            if states.get("bob") is False:
                break
            time.sleep(0.05)
        self.assertEqual(states, {"alice": True, "bob": False})

    def test_errors(self):
        alice = self.client("alice")
        with self.assertRaises(LabShareError):
            alice.send("nobody", "hi")
        with self.assertRaises(LabShareError):
            alice.send("alice", "   ")
        with self.assertRaises(LabShareError):
            alice.send("alice", "x" * (MAX_MESSAGE_BYTES + 1))
        with self.assertRaises(LabShareError):
            alice.send("alice", "hi", kind="virus")

    def test_bad_username_rejected(self):
        with self.assertRaises(LabShareError):
            LabShareClient("bad name!", "127.0.0.1", self.server.port).connect()

    def test_reconnect_replaces_old_session(self):
        first = self.client("alice")
        second = self.client("alice")
        self.assertEqual(second.list_users()[0]["username"], "alice")
        # the old connection was dropped by the host, but the client heals itself
        self.assertEqual(first.list_users()[0]["username"], "alice")

    def test_large_message_roundtrip(self):
        alice = self.client("alice")
        body = ("line with unicode ✓ and \"quotes\"\n" * 20000)[:MAX_MESSAGE_BYTES // 2]
        alice.send("alice", body, "code")
        self.assertEqual(alice.inbox()[0]["body"], body)


class TokenTests(ServerTests):
    token = "s3cret"

    def client(self, name, token="s3cret"):
        return super().client(name, token)

    def test_wrong_token_rejected(self):
        with self.assertRaises(LabShareError):
            LabShareClient("eve", "127.0.0.1", self.server.port, "nope").connect()
        with self.assertRaises(LabShareError):
            LabShareClient("eve", "127.0.0.1", self.server.port).connect()


if __name__ == "__main__":
    unittest.main()
