import pickle

import serial
import time

import cv2
import mediapipe as mp
import numpy as np

model_dict = pickle.load(open('./model.p', 'rb'))
model = model_dict['model']

arduino = serial.Serial('COM6', 9600, timeout=1)
time.sleep(2)  # wait for Arduino reset


cap = cv2.VideoCapture(0)

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

CLASSES = [
    "Hand_and_wrist_stretch_relax",
    "Hand_and_wrist_stretch_left",
    "Hand_and_wrist_stretch_right",
    "Grip_power_relax",
    "Grip_power_squeeze",
    "Extending_the_wrist_relax",
    "Extending_the_wrist_down",
    "Extending_the_wrist_up",
    "Turning_a_bottle_relax",
    "Turning_a_bottle_left",
    "Turning_a_bottle_right",
    "Finger_flexion_relax",
    "Finger_flexion_fist",
    "Flexion_relax",
    "Flexion_compress",
    "Bending_of_knuckle_relax",
    "Bending_of_knuckle_bending",
    "Abduction_and_adduction_adduction",
    "Abduction_and_adduction_abduction",
    "Finger_flexion_with_ball_relax",
    "Finger_flexion_with_ball_compress",
    "Opposition_relax",
    "Opposition_compress",
    "Thumb_movement_abduction",
    "Thumb_movement_flexion"
]

labels_dict = {i: label for i, label in enumerate(CLASSES)}

last_prediction = "WAITING..."

prev_sent = ""


while True:
    ret, frame = cap.read()
    if not ret:
        continue

    H, W, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = hands.process(frame_rgb)

    # DEFAULT: do nothing (freeze state)
    show_prediction = False

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]  # FORCE ONE HAND

        x_ = []
        y_ = []
        data_aux = []

        for lm in hand_landmarks.landmark:
            x_.append(lm.x)
            y_.append(lm.y)

        for lm in hand_landmarks.landmark:
            data_aux.append(lm.x - min(x_))
            data_aux.append(lm.y - min(y_))

        # 🔒 STRICT FEATURE CHECK
        if len(data_aux) == 42:
            prediction = model.predict([np.asarray(data_aux)])
            last_prediction = prediction[0]
            show_prediction = True

            if last_prediction != prev_sent:
                 arduino.write((last_prediction + "\n").encode())
                 prev_sent = last_prediction

            # Bounding box
            x1 = int(min(x_) * W) - 10
            y1 = int(min(y_) * H) - 10
            x2 = int(max(x_) * W) + 10
            y2 = int(max(y_) * H) + 10

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

    # 🧊 ALWAYS SHOW LAST VALID PREDICTION
    cv2.putText(
        frame,
        last_prediction,
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )

    cv2.imshow("Exercise Translator", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break



cap.release()
cv2.destroyAllWindows()
