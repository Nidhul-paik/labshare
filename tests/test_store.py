import os
import tempfile
import unittest

from labshare.store import MessageStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MessageStore(os.path.join(self.tmp.name, "t.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_usernames_are_case_insensitive_and_keep_first_spelling(self):
        self.assertEqual(self.store.register_user("Alice"), "Alice")
        self.assertEqual(self.store.register_user("alice"), "Alice")
        self.assertEqual(self.store.canonical_name("ALICE"), "Alice")
        self.assertIsNone(self.store.canonical_name("bob"))

    def test_inbox_and_mark_read(self):
        self.store.register_user("a")
        self.store.register_user("b")
        mid = self.store.save_message("a", "b", "code", "x.py", "print(1)")
        self.assertEqual(self.store.unread_count("b"), 1)
        inbox = self.store.inbox("B")
        self.assertEqual(inbox[0]["body"], "print(1)")
        self.assertEqual(inbox[0]["filename"], "x.py")
        self.assertFalse(self.store.mark_read(mid, "a"))  # not the recipient
        self.assertTrue(self.store.mark_read(mid, "b"))
        self.assertEqual(self.store.unread_count("b"), 0)

    def test_client_id_prevents_duplicates(self):
        first = self.store.save_message("a", "b", "text", None, "hi", "id1")
        again = self.store.save_message("a", "b", "text", None, "hi", "id1")
        self.assertEqual(first, again)
        self.assertEqual(self.store.unread_count("b"), 1)

    def test_list_users_online_flag(self):
        self.store.register_user("a")
        self.store.register_user("b")
        users = {u["username"]: u["online"] for u in self.store.list_users({"A"})}
        self.assertEqual(users, {"a": True, "b": False})

    def test_unicode_roundtrip(self):
        self.store.register_user("a")
        self.store.save_message("a", "a", "text", None, "héllo ✓ 日本語")
        self.assertEqual(self.store.inbox("a")[0]["body"], "héllo ✓ 日本語")


if __name__ == "__main__":
    unittest.main()
