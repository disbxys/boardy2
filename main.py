from flask_app import app


if __name__ == "__main__":
    PORT = 5000

    app.run(port=PORT, debug=True)