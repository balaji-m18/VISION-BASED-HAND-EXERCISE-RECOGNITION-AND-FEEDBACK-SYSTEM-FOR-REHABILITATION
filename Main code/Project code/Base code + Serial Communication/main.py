import sys
from PyQt6.QtWidgets import QApplication

from camera_worker import CameraWorker
from workout_engine import WorkoutEngine
from ui_main import MainWindow

MODEL_PATH = r"C:\Major Project\sign-language-detector-python-master\model.p"


def main():
    app = QApplication(sys.argv)

    camera_worker = CameraWorker(MODEL_PATH)
    workout_engine = WorkoutEngine()

    window = MainWindow(camera_worker, workout_engine)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
