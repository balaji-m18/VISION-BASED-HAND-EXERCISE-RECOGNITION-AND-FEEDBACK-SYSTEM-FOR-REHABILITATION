import cv2
import json
import matplotlib.pyplot as plt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QWidget,
    QVBoxLayout, QHBoxLayout, QProgressBar,
    QDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


# ==========================================================
# REPORT DIALOG (PRODUCTION LEVEL)
# ==========================================================

class ReportDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Workout Report")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        final_score = report["final_accuracy"]

        title = QLabel(f"Final Accuracy: {final_score:.2f}%")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        for ex in report["exercise_breakdown"]:
            if ex["accuracy"] is None:
                label = QLabel(f"{ex['exercise']} : NA")
            else:
                label = QLabel(f"{ex['exercise']} : {ex['accuracy']:.2f}%")
            layout.addWidget(label)

        # ===== Embedded Matplotlib Graph =====

# ==========================================================
# MAIN WINDOW
# ==========================================================

class MainWindow(QMainWindow):
    def __init__(self, camera_worker, workout_engine):
        super().__init__()

        self.camera_worker = camera_worker
        self.workout_engine = workout_engine

        self.is_running = False

        self.setWindowTitle(" Hand Therapy Trainer")
        self.setMinimumSize(1100, 850)

        self._setup_ui()
        self._connect_signals()
        self._apply_styles()

    # ======================================================
    # UI SETUP
    # ======================================================

    def _setup_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        central_widget.setLayout(main_layout)

        # ===== Glass Card =====
        self.glass_card = QWidget()
        self.glass_card.setFixedWidth(950)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(15)
        shadow.setColor(Qt.GlobalColor.black)
        self.glass_card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout()
        card_layout.setSpacing(25)
        card_layout.setContentsMargins(40, 40, 40, 40)
        self.glass_card.setLayout(card_layout)

        main_layout.addWidget(self.glass_card)

        # Phase
        self.phase_label = QLabel("Press Start")
        self.phase_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.phase_label)

        # Status Indicator
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        # Progress
        self.progress = QProgressBar()
        self.progress.setMaximum(len(self.workout_engine.WORKOUT_PLAN))
        card_layout.addWidget(self.progress)

        # Camera
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(820, 500)
        self.camera_label.setScaledContents(False)
        card_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Timer
        self.timer_label = QLabel("00")
        self.timer_label.setFont(QFont("Arial", 56, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.timer_label)

        # Feedback
        self.feedback_label = QLabel("")
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.feedback_label)

        self.accuracy_label = QLabel("Live Score: 0%")
        self.accuracy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.accuracy_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.finish_btn = QPushButton("Finish")

        for btn in [self.start_btn, self.pause_btn, self.resume_btn, self.finish_btn]:
            btn.setFixedSize(140, 45)
            button_layout.addWidget(btn)

        card_layout.addLayout(button_layout)

    # ======================================================
    # STYLING
    # ======================================================

    def _apply_styles(self):

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e3c72,
                    stop:1 #2a5298
                );
            }

            QLabel { color: white; }

            QWidget#glass {
                background: rgba(255,255,255,0.08);
                border-radius: 25px;
            }

            QPushButton {
                background-color: rgba(255,255,255,0.08);
                color: white;
                border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.2);
            }

            QPushButton:hover {
                border: 1px solid #00c6ff;
            }

            QProgressBar {
                border: none;
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                text-align: center;
                height: 18px;
            }

            QProgressBar::chunk {
                background-color: #00c6ff;
                border-radius: 10px;
            }
        """)

    # ======================================================
    # SIGNALS
    # ======================================================

    def _connect_signals(self):

        self.camera_worker.frame_ready.connect(self.update_frame)
        self.camera_worker.prediction_ready.connect(
            self.workout_engine.process_prediction
        )

        self.workout_engine.phase_changed.connect(self.update_phase)
        self.workout_engine.rest_started.connect(self.start_rest)
        self.workout_engine.timer_updated.connect(self.update_timer)
        self.workout_engine.live_feedback.connect(self.update_feedback)
        self.workout_engine.workout_completed.connect(self.show_final_report)

        self.start_btn.clicked.connect(self.start_workout)
        self.pause_btn.clicked.connect(self.pause_workout)
        self.resume_btn.clicked.connect(self.resume_workout)
        self.finish_btn.clicked.connect(self.finish_workout)

    # ======================================================
    # UPDATE METHODS
    # ======================================================

    def update_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        scaled = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        x = (scaled.width() - self.camera_label.width()) // 2
        y = (scaled.height() - self.camera_label.height()) // 2

        self.camera_label.setPixmap(
            scaled.copy(x, y, self.camera_label.width(), self.camera_label.height())
        )

    def update_phase(self, phase_name, exercise_index, phase_index):
        self.phase_label.setText(phase_name)
        self.progress.setValue(exercise_index)

    def start_rest(self, duration):
        self.phase_label.setText("REST PHASE - Remove Hand")
        self.timer_label.setText(str(duration))

    def update_timer(self, remaining):
        self.timer_label.setText(str(remaining))

    def update_feedback(self, score, message):
        self.feedback_label.setText(message)
        self.accuracy_label.setText(f"Live Score: {score}%")

    # ======================================================
    # BUTTON LOGIC
    # ======================================================

    def start_workout(self):
        if not self.is_running:
            self.is_running = True
            self.status_label.setText("Status: Running")
            self.camera_worker.start()
            self.workout_engine.start_workout()
            self.start_btn.setEnabled(False)

    def pause_workout(self):
        self.status_label.setText("Status: Paused")
        self.workout_engine.pause()

    def resume_workout(self):
        self.status_label.setText("Status: Running")
        self.workout_engine.resume()

    def finish_workout(self):
        self.status_label.setText("Status: Stopped")
        self.camera_worker.stop()
        self.workout_engine.stop()
        self.phase_label.setText("Workout Stopped")
        self.is_running = False
        self.start_btn.setEnabled(True)

    # ======================================================
    # FINAL REPORT
    # ======================================================

    def show_final_report(self, report):
        self.camera_worker.stop()

        with open("workout_history.json", "a") as f:
            json.dump(report, f)
            f.write("\n")

        dialog = ReportDialog(report, self)
        dialog.exec()
