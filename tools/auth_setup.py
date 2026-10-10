#!/usr/bin/env python3
"""Provisioning CLI for RPi Dashboard authentication.

Subcommands:
  expert     Set or update the Expert password
  admin      Set or update the Admin password
  api-key    Create a new API key (prints raw value once)
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import subprocess
import sys
from pathlib import Path

# Ensure we can import from rpi_dashboard
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rpi_dashboard.auth import AuthStore, Role


def _detect_askpass() -> str | None:
    """Return the askpass program path if available and appropriate.

    Prefers SSH_ASKPASS if set and it is an executable regular file.
    Falls back to /usr/bin/ssh-askpass if it exists, is an executable
    regular file, and DISPLAY is set. Returns None if no graphical
    askpass is available.
    """
    # Explicit SSH_ASKPASS takes precedence
    ssh_askpass = os.environ.get("SSH_ASKPASS")
    if ssh_askpass:
        p = Path(ssh_askpass)
        if p.is_file() and os.access(p, os.X_OK):
            return ssh_askpass

    # Graphical environment detected via DISPLAY
    if os.environ.get("DISPLAY"):
        default_askpass = Path("/usr/bin/ssh-askpass")
        if default_askpass.is_file() and os.access(default_askpass, os.X_OK):
            return str(default_askpass)

    return None


def _prompt_password(prompt: str, confirm: bool = True) -> str:
    """Prompt for a password using askpass or getpass fallback."""
    askpass = _detect_askpass()
    if askpass:
        try:
            # ssh-askpass reads the prompt from the first argument
            # and writes the password to stdout
            result = subprocess.run(
                [askpass, prompt],
                capture_output=True,
                text=True,
                check=True,
            )
            password = result.stdout.rstrip("\n")
            if confirm:
                result2 = subprocess.run(
                    [askpass, f"{prompt} (confirm)"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                confirm_pw = result2.stdout.rstrip("\n")
                if password != confirm_pw:
                    raise ValueError("Passwords do not match")
            return password
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fall through to getpass
            pass

    # Fallback: getpass (works on TTY)
    password = getpass.getpass(prompt + ": ")
    if confirm:
        confirm_pw = getpass.getpass(f"{prompt} (confirm): ")
        if password != confirm_pw:
            raise ValueError("Passwords do not match")
    return password


def _get_auth_store(args: argparse.Namespace) -> AuthStore:
    """Get AuthStore instance from args or default path."""
    path = Path(args.auth_file).expanduser().resolve()
    return AuthStore(path)


def _cmd_expert(args: argparse.Namespace) -> int:
    """Set or update the Expert password."""
    store = _get_auth_store(args)

    try:
        password = _prompt_password("Expert password")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130

    if not password:
        print("Error: password cannot be empty", file=sys.stderr)
        return 1

    store.set_expert(password)
    print(f"Expert password set (stored in {args.auth_file})")
    return 0


def _cmd_admin(args: argparse.Namespace) -> int:
    """Set or update the Admin password."""
    store = _get_auth_store(args)

    try:
        password = _prompt_password("Admin password")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130

    if not password:
        print("Error: password cannot be empty", file=sys.stderr)
        return 1

    store.set_admin(password)
    print(f"Admin password set (stored in {args.auth_file})")
    return 0


def _cmd_api_key(args: argparse.Namespace) -> int:
    """Create a new API key."""
    store = _get_auth_store(args)

    label = args.label
    if not label or not label.strip():
        print("Error: label must not be empty", file=sys.stderr)
        return 1
    role_name = args.role.lower() if args.role else "basic"

    try:
        role = Role[role_name.upper()]
    except KeyError:
        print(f"Error: invalid role '{args.role}'. Must be one of: basic, expert, admin", file=sys.stderr)
        return 1

    raw_token = secrets.token_urlsafe(32)
    store.create_api_key(raw_token, role, label)

    # Print raw token exactly once to stdout
    print(raw_token)
    print(f"API key created with role={role.name.lower()}, label='{label}'", file=sys.stderr)
    print(f"Store location: {args.auth_file}", file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auth_setup",
        description="RPi Dashboard authentication provisioning CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s expert                    # Set Expert password
  %(prog)s admin                     # Set Admin password
  %(prog)s api-key "ci-build" admin  # Create Admin API key labelled "ci-build"
  %(prog)s --auth-file /etc/rpi-dashboard/auth.json expert

Passwords are never passed as command-line arguments.
When $DISPLAY or $SSH_ASKPASS is set, ssh-askpass is used for prompting.
Otherwise, getpass is used (requires a TTY).
""",
    )
    parser.add_argument(
        "--auth-file",
        default="~/rpi-dashboard/auth.json",
        help="Path to auth.json (default: ~/rpi-dashboard/auth.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # expert subcommand
    subparsers.add_parser("expert", help="Set or update Expert password")

    # admin subcommand
    subparsers.add_parser("admin", help="Set or update Admin password")

    # api-key subcommand
    api_key_parser = subparsers.add_parser(
        "api-key",
        help="Create a new API key (raw value printed once to stdout)",
    )
    api_key_parser.add_argument(
        "label",
        help="Human-readable label for the key",
    )
    api_key_parser.add_argument(
        "role",
        nargs="?",
        default="basic",
        choices=["basic", "expert", "admin"],
        help="Role for the API key (default: basic)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    if args.command == "expert":
        return _cmd_expert(args)
    elif args.command == "admin":
        return _cmd_admin(args)
    elif args.command == "api-key":
        return _cmd_api_key(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
