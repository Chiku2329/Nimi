"""Create Nimi's NIMI_USERS_JSON password-hash configuration.

Run locally: python tools/create_users.py
The script prints password hashes only. Never commit its output.
"""
import getpass
import hashlib
import json
import re
import secrets
import sys

ITERATIONS = 600_000
MAX_USERS = 20


def main():
    users = {}
    print("Create up to 20 individual Nimi accounts.")
    print("Use a unique username and a unique password of at least 14 characters.")
    print("Do not reuse your email or another website's password.\n")

    while len(users) < MAX_USERS:
        username = input(f"Username for account {len(users) + 1} (blank to finish): ").strip().lower()
        if not username:
            break
        if not re.fullmatch(r"[a-z0-9_.-]{3,64}", username):
            print("Use 3-64 characters: lowercase letters, numbers, dot, underscore or hyphen.")
            continue
        if username in users:
            print("That username already exists.")
            continue

        password = getpass.getpass("Password (hidden): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            print("Passwords do not match.")
            continue
        if len(password) < 14:
            print("Password must be at least 14 characters.")
            continue

        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        users[username] = f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"
        print(f"Added {username}.\n")

    if not users:
        print("No accounts created.", file=sys.stderr)
        sys.exit(1)

    print("\nCopy the following JSON into Blitz as the NIMI_USERS_JSON secret.")
    print("Treat it as confidential. Do not paste it into GitHub or this chat.\n")
    print(json.dumps(users, separators=(",", ":")))


if __name__ == "__main__":
    main()
