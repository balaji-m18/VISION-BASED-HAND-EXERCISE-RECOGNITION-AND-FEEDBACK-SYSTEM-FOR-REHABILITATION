import pickle
import cv2
import mediapipe as mp
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from collections import deque


class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    prediction_ready = pyqtSignal(str, bool)
    # (predicted_label, hand_detected)

    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path
        self.running = False

        # Load ML model
        model_dict = pickle.load(open(self.model_path, 'rb'))
        self.model = model_dict['model']

        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils   # ✅ ADDED
        self.mp_drawing_styles = mp.solutions.drawing_styles  # ✅ ADDED

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,   # 🔥 changed for real-time tracking
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Webcam
        self.cap = cv2.VideoCapture(0)

        # Prediction smoothing buffer
        self.prediction_buffer = deque(maxlen=5)

    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            predicted_label = "WAITING..."
            hand_detected = False
            
            if results.multi_hand_landmarks:
                hand_detected = True
                hand_landmarks = results.multi_hand_landmarks[0]
                
                self.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )
                x_ = []
                y_ = []
                data_aux = []

                for lm in hand_landmarks.landmark:
                    x_.append(lm.x)
                    y_.append(lm.y)

                for lm in hand_landmarks.landmark:
                    data_aux.append(lm.x - min(x_))
                    data_aux.append(lm.y - min(y_))

                if len(data_aux) == 42:
                    prediction = self.model.predict([np.asarray(data_aux)])
                    self.prediction_buffer.append(prediction[0])

                    if len(self.prediction_buffer) == 5:
                        predicted_label = max(
                            set(self.prediction_buffer),
                            key=self.prediction_buffer.count
                    )

            self.frame_ready.emit(frame)
            self.prediction_ready.emit(predicted_label, hand_detected)

    # 🔥 CLEANUP AFTER LOOP ENDS
        self.cap.release()

    def stop(self):
        self.running = False
