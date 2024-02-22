

from flask_app import app


def launch_app(host=None, port=5000):
    if host is not None:
        app.run(host=host, port=port, debug=True)
    else:
        app.run(port=port, debug=True)


if __name__ == "__main__":
    launch_app()
