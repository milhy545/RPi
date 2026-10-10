def app(environ, start_response):
    """Minimal WSGI entrypoint for Vercel preview deployments."""
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"RPi Dashboard service is intended to run on Raspberry Pi.\n"]


application = app


def main():
    print("Hello from rpi!")


if __name__ == "__main__":
    main()
