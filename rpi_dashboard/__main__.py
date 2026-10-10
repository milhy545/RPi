"""Package entrypoint for the production RPi Dashboard server."""

import webserver


def main() -> None:
    """Start the supported dashboard server entrypoint."""
    webserver.main()


if __name__ == "__main__":
    main()
