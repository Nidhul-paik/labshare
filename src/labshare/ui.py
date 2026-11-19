"""Menu-driven terminal interface.

Plain ``print``/``input`` only (no colours, no curses), so it behaves the same in
Windows cmd.exe, PowerShell, Windows Terminal and any Linux terminal.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .client import LabShareClient, LabShareError
from .clipboard import copy_to_clipboard
from .config import KINDS, MAX_MESSAGE_BYTES

END_MARKER = ".END"
RECEIVED_DIR = "received"


def read_multiline() -> Optional[str]:
    print("\nType or paste your content below.")
    print(f"When finished, type {END_MARKER} on a line by itself and press Enter.")
    print("-" * 50)
    lines: List[str] = []
    total = 0
    while True:
        try:
            line = input()
        except EOFError:  # Ctrl+D (Linux) / Ctrl+Z then Enter (Windows)
            break
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None
        if line.strip() == END_MARKER:
            break
        total += len(line.encode("utf-8")) + 1
        if total > MAX_MESSAGE_BYTES:
            print("Message limit is 1 MB. Nothing was sent.")
            return None
        lines.append(line)
    return "\n".join(lines)


def preview(message: dict, width: int = 40) -> str:
    first = next((ln.strip() for ln in message["body"].splitlines() if ln.strip()), "")
    return first if len(first) <= width else first[: width - 3] + "..."


def show_users(client: LabShareClient) -> List[dict]:
    users = client.list_users()
    if not users:
        print("\nNo registered users yet.")
        return users
    print("\nUsers:")
    for index, user in enumerate(users, 1):
        status = "ONLINE" if user["online"] else "OFFLINE"
        me = "  (you)" if user["username"].lower() == client.username.lower() else ""
        print(f"  {index}. {user['username']:<20} [{status}]{me}")
    return users


def choose_recipient(users: List[dict]) -> Optional[str]:
    raw = input("\nRecipient (number or username, Enter to cancel): ").strip()
    if not raw:
        return None
    if raw.isdigit() and 1 <= int(raw) <= len(users):
        return users[int(raw) - 1]["username"]
    return raw


def choose_kind() -> str:
    print("\nWhat are you sending?")
    for index, kind in enumerate(KINDS, 1):
        print(f"  {index}. {kind}")
    raw = input("Choose [1]: ").strip() or "1"
    if raw.isdigit() and 1 <= int(raw) <= len(KINDS):
        return KINDS[int(raw) - 1]
    return raw if raw in KINDS else "text"


def send_flow(client: LabShareClient) -> None:
    users = show_users(client)
    if not users:
        return
    recipient = choose_recipient(users)
    if not recipient:
        return
    kind = choose_kind()
    filename = None
    if kind == "code":
        filename = input("Suggested file name for the receiver (optional, e.g. solution.py): ").strip() or None
    body = read_multiline()
    if body is None or not body.strip():
        print("Nothing to send.")
        return
    reply = client.send(recipient, body, kind, filename)
    state = "is online" if reply["recipient_online"] else "is offline and will see it next time"
    print(f"\n[LabShare] Sent to {reply['to']} (message #{reply['id']}); {reply['to']} {state}.")


def _save_message(message: dict) -> None:
    default = message.get("filename") or f"message_{message['id']}.txt"
    raw = input(f"Save as [{default}] (saved in the '{RECEIVED_DIR}' folder unless you give a full path): ").strip()
    target = Path(raw or default).expanduser()
    if not target.is_absolute():
        target = Path(RECEIVED_DIR) / target
    if target.exists() and input(f"{target} exists. Overwrite? [y/N]: ").strip().lower() != "y":
        print("Not saved.")
        return
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(message["body"], encoding="utf-8", newline="")
        print(f"Saved to {target.resolve()}")
    except OSError as exc:
        print(f"Could not save file: {exc}")


def open_message(client: LabShareClient, message: dict) -> None:
    extra = f"    File: {message['filename']}" if message.get("filename") else ""
    print("\n" + "=" * 60)
    print(f"From: {message['sender']}    Type: {message['kind']}{extra}    Received: {message['created_at']}")
    print("=" * 60)
    print(message["body"])
    print("=" * 60)
    while True:
        print("\n1. Copy to clipboard\n2. Save to file\n3. Mark as read and go back\n4. Go back (keep unread)")
        choice = input("Choose: ").strip()
        if choice == "1":
            if copy_to_clipboard(message["body"]):
                print("[LabShare] Copied to clipboard.")
            else:
                print("[LabShare] No clipboard tool found (Linux: install xclip or wl-clipboard). Use 'Save to file' instead.")
        elif choice == "2":
            _save_message(message)
        elif choice == "3":
            client.mark_read(message["id"])
            print("Marked as read.")
            return
        elif choice == "4":
            return
        else:
            print("Choose 1-4.")


def inbox_flow(client: LabShareClient) -> None:
    while True:
        messages = client.inbox()
        if not messages:
            print("\nYour inbox is empty.")
            return
        print(f"\nYou have {len(messages)} unread message(s):")
        for index, m in enumerate(messages, 1):
            print(f"  {index}. #{m['id']:<4} {m['sender']:<16} {m['kind']:<8} {m['created_at']}  {preview(m)}")
        raw = input("Open message number (Enter to go back): ").strip()
        if not raw:
            return
        if not raw.isdigit() or not 1 <= int(raw) <= len(messages):
            print("Invalid selection.")
            continue
        open_message(client, messages[int(raw) - 1])


def _unread_label(client: LabShareClient) -> str:
    try:
        count = client.unread_count()
    except (OSError, LabShareError):
        return " (host not reachable)"
    return f" ({count} unread)" if count else ""


def run(client: LabShareClient) -> None:
    actions = {"1": show_users, "2": send_flow, "3": inbox_flow}
    try:
        while True:
            print("\n========== LABSHARE ==========")
            print(f"User: {client.username}    Host: {client.host}:{client.port}")
            print("1. Show users")
            print("2. Send text / code / command")
            print(f"3. Inbox{_unread_label(client)}")
            print("4. Exit")
            choice = input("Select: ").strip()
            if choice == "4":
                break
            action = actions.get(choice)
            if action is None:
                print("Invalid option.")
                continue
            try:
                action(client)
            except LabShareError as exc:
                print(f"[LabShare] {exc}")
            except OSError as exc:
                print(f"[LabShare] Connection problem: {exc}")
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        client.close()
    print("Goodbye.")
