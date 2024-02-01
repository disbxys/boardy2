import sys
import time

from PyQt6.QtCore import QThread, QUrl, QRect, QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView


PORT = 5000
ROOT_URL = "http://localhost:{}/".format(PORT)


class FlaskThread(QThread):
    def __init__(self, application):
        QThread.__init__(self)
        self.application = application

    def __del__(self):
        self.wait()

    def run(self):
        self.application.run(port=PORT)


class FlaskGui(QMainWindow):
    def __init__(self, application):
        super().__init__()

        self.setWindowTitle("Flask Desktop")
        self.setMinimumSize(QSize(1400, 1000))

        self.flask_thread = FlaskThread(application)

        self.webview = QWebEngineView()
        self.setCentralWidget(self.webview)
        self.webview.load(QUrl(ROOT_URL))
        
        self.webview.loadStarted.connect(self.load_started)
        self.webview.loadProgress.connect(self.load_progress)
        self.webview.loadFinished.connect(self.load_finished)

        self.flask_thread.start()


    def load_started(self):
        print(self.webview.url().url(), ": load started")

    def load_progress(self, prog):
        print(self.webview.url().url(), ":load progress", prog)

    def load_finished(self):
        print(self.webview.url().url(), ": load finished")


def run_gui():
    qtapp = QApplication(sys.argv)

    flask_gui = FlaskGui(app)

    qtapp.aboutToQuit.connect(flask_gui.flask_thread.terminate)

    flask_gui.show()

    sys.exit(qtapp.exec())


if __name__ == "__main__":
    from flask_app import app
    
    app.run(port=PORT, debug=True)

    # run_gui()