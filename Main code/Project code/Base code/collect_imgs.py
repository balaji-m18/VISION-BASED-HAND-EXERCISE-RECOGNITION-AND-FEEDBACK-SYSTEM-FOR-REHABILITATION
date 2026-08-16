import os
import cv2

DATA_DIR = './data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

CLASSES = [
   
    
    
    "Thumb_movement_flexion",
    "Opposition_compress",
    "Finger_flexion_fist",
    "Finger_flexion_relax",
    "Grip_power_relax",
    "Grip_power_squeeze",
    "Abduction_and_adduction_abduction",
    "Flexion_compress",
    "Bending_of_knuckle_relax",
    "Flexion_relax",
    "Abduction_and_adduction_adduction",
    "Bending_of_knuckle_bending",
    "Opposition_relax",
   
    "Thumb_movement_abduction",
    
]

dataset_size = 100

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

for class_name in CLASSES:
    class_path = os.path.join(DATA_DIR, class_name)
    if not os.path.exists(class_path):
        os.makedirs(class_path)

    print(f'📸 Collecting data for: {class_name}')

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.putText(
            frame,
            f'Ready for {class_name}? Press Q',
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.imshow('frame', frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    counter = 0
    while counter < dataset_size:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow('frame', frame)
        cv2.imwrite(
            os.path.join(class_path, f'{counter}.jpg'),
            frame
        )

        counter += 1
        cv2.waitKey(25)

cap.release()
cv2.destroyAllWindows()
