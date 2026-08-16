from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import requests
import serial
import time
import threading

BLYNK_AUTH = "bAZ4c_KYJ9IAcvsvqqIEc-QmySmEGob5"

    # ✅ GLOBAL BLYNK HELPER
last_values = {}

def send_to_blynk(pin, value):
    global last_values

    if last_values.get(pin) == value:
        return

    last_values[pin] = value

    def send():
        try:
            url = f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH}&{pin}={value}"
            requests.get(url, timeout=0.2)
        except:
            pass

    # ✅ Run in background thread (NON-BLOCKING)
    threading.Thread(target=send, daemon=True).start()

class WorkoutEngine(QObject):

        # Signals to UI
        phase_changed = pyqtSignal(str, int, int)
        rest_started = pyqtSignal(int)
        timer_updated = pyqtSignal(int)
        live_feedback = pyqtSignal(int, str)
        workout_completed = pyqtSignal(dict)

        def __init__(self):
            super().__init__()
            try:
                self.arduino = serial.Serial("COM6", 115200, timeout=1)
            except:
                self.arduino = None

            # ===== REPORT TRACKING =====
            self.exercise_scores = []
            self.current_exercise_score = 0
            self.current_exercise_frames = 0

            self.last_sent_message = ""

            # ===== WORKOUT PLAN =====
            self.WORKOUT_PLAN = [
                {
                    "exercise_name": "Finger_flexion",
                    "phases": [
                        ("Finger_flexion_relax", 10),
                        ("Finger_flexion_fist", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Flexion",
                    "phases": [
                        ("Flexion_relax", 10),
                        ("Flexion_compress", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Abduction_and_adduction",
                    "phases": [
                        ("Abduction_and_adduction_adduction", 10),
                        ("Abduction_and_adduction_abduction", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Opposition",
                    "phases": [
                        ("Opposition_relax", 10),
                        ("Opposition_compress", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Thumb_movement",
                    "phases": [
                        ("Thumb_movement_abduction", 10),
                        ("Thumb_movement_flexion", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Bending_of_knuckle",
                    "phases": [
                        ("Bending_of_knuckle_relax", 10),
                        ("Bending_of_knuckle_bending", 10),
                    ],
                    "rest": 15
                },
                {
                    "exercise_name": "Grip_power",
                    "phases": [
                        ("Grip_power_relax", 10),
                        ("Grip_power_squeeze", 10),
                    ],
                    "rest": 15
                },
            ]

            # ===== STATE =====
            self.current_exercise_index = 0
            self.current_phase_index = 0
            self.in_rest = False

            self.remaining_time = 0
            self.total_score_accumulated = 0
            self.total_frames_counted = 0

            self.timer = QTimer()
            self.timer.timeout.connect(self._update_timer)

            self.current_expected_label = None
            self.current_expected_exercise_index = 0

        # ==============================
        # CONTROL METHODS
        # ==============================
        
        def start_workout(self):
            self.current_exercise_index = 0
            self.current_phase_index = 0
            self.total_score_accumulated = 0
            self.total_frames_counted = 0
            self.exercise_scores = []
            self.in_rest = False
            self._start_phase()

        def pause(self):
            self.timer.stop()

        def resume(self):
            if not self.in_rest:
                if self.current_exercise_frames > 0:
                    self.timer.start(1000)
            else:
                self.timer.start(1000)

        def stop(self):
            self.timer.stop()
            exercise_accuracy = None

            if self.current_exercise_index < len(self.WORKOUT_PLAN):
                current_exercise_name = self.WORKOUT_PLAN[self.current_exercise_index]["exercise_name"]
                
                if len(self.exercise_scores) == self.current_exercise_index:
                    self.exercise_scores.append({
                    "exercise": current_exercise_name,
                    "accuracy": exercise_accuracy,
                })
                    
            for i in range(len(self.exercise_scores), len(self.WORKOUT_PLAN)):
                self.exercise_scores.append({
                "exercise": self.WORKOUT_PLAN[i]["exercise_name"],
                "accuracy": None
            })
                
            final_accuracy = (
            self.total_score_accumulated / self.total_frames_counted
            if self.total_frames_counted > 0 else 0
        )
            report = {
            "final_accuracy": final_accuracy,
            "exercise_breakdown": self.exercise_scores,
            "total_exercises": len(self.WORKOUT_PLAN)
        }
            self.workout_completed.emit(report)

        # ==============================
        # PHASE / REST MANAGEMENT
        # ==============================

        def _start_phase(self):
            if self.current_phase_index == 0:
                self.current_exercise_score = 0
                self.current_exercise_frames = 0

            exercise = self.WORKOUT_PLAN[self.current_exercise_index]
            phase_name, duration = exercise["phases"][self.current_phase_index]

            self.current_expected_label = phase_name
            self.current_expected_exercise_index = self.current_exercise_index

            self.remaining_time = duration
            self.in_rest = False

            self.phase_changed.emit(
                phase_name,
                self.current_exercise_index + 1,
                self.current_phase_index + 1
            )

            self.timer.start(1000)
            exercise_name = self.WORKOUT_PLAN[self.current_exercise_index]["exercise_name"]
            clean_name = exercise_name.replace("_", " ")

            send_to_blynk("V0", clean_name)

        def _start_rest(self):
            rest_duration = self.WORKOUT_PLAN[self.current_exercise_index]["rest"]

            self.remaining_time = rest_duration
            self.in_rest = True

            self.rest_started.emit(rest_duration)

            # ✅ REST TIMER ALWAYS RUNS
            self.timer.start(1000)

            send_to_blynk("V2", "Resting...")

        def _update_timer(self):
            self.remaining_time -= 1
            self.timer_updated.emit(self.remaining_time)

            if self.remaining_time <= 0:
                self.timer.stop()

                if self.in_rest:
                    self._next_exercise()
                else:
                    self._next_phase()

        def _next_phase(self):
            exercise = self.WORKOUT_PLAN[self.current_exercise_index]

            if self.current_phase_index < len(exercise["phases"]) - 1:
                self.current_phase_index += 1
                self._start_phase()
            else:
                self._start_rest()

        def _next_exercise(self):

            # ✅ Save exercise accuracy
            if self.current_exercise_frames > 0:
                exercise_accuracy = self.current_exercise_score / self.current_exercise_frames
                send_to_blynk("V1", round(exercise_accuracy, 2))
            else:
                exercise_accuracy = 0

            self.exercise_scores.append({
                "exercise": self.WORKOUT_PLAN[self.current_exercise_index]["exercise_name"],
                "accuracy": exercise_accuracy
            })

            if self.current_exercise_index < len(self.WORKOUT_PLAN) - 1:
                self.current_exercise_index += 1
                self.current_phase_index = 0
                self._start_phase()
            else:
                # ✅ Final Report
                final_accuracy = (
                    self.total_score_accumulated / self.total_frames_counted
                    if self.total_frames_counted > 0 else 0
                )
                send_to_blynk("V1", round(final_accuracy, 2))

                self.timer.stop()

                report = {
                    "final_accuracy": final_accuracy,
                    "exercise_breakdown": self.exercise_scores,
                    "total_exercises": len(self.WORKOUT_PLAN)
                }

                self.workout_completed.emit(report)
                self.send_final_report_to_arduino(report)

        # ==============================
        # ML PREDICTION INPUT
        # ==============================

        def process_prediction(self, detected_label, hand_detected):

            # ✅ Ignore ML during REST
            if self.in_rest:
                return

            # ❌ No hand → STOP timer immediately
            if not hand_detected:
                self.timer.stop()
                score = 0
                message = "No Hand Detected ❌"
                self.live_feedback.emit(score, message)

                send_to_blynk("V2", message)   # Message
                send_to_blynk("V3", score)     # Live Score

                return

            score = self._calculate_score(detected_label)
            

            # ❌ Wrong exercise → STOP timer
            if score == 0:
                self.timer.stop()
            else:
                # ✅ Resume timer only if correct
                if not self.timer.isActive():
                    self.timer.start(1000)

            # ✅ Accumulate scores only if hand detected
            self.total_score_accumulated += score
            self.total_frames_counted += 1
            self.current_exercise_score += score
            self.current_exercise_frames += 1

            message = self._score_message(score)
            self.live_feedback.emit(score, message)

            send_to_blynk("V2", message)   # Message
            send_to_blynk("V3", score)     # Live Score

            self.frame_skip_counter = getattr(self, "frame_skip_counter", 0) + 1

            if self.frame_skip_counter % 5 == 0:
                send_to_blynk("V2", message)
                send_to_blynk("V3", score)

            

    # ✅ Send only if message changed
            if message != self.last_sent_message:
                self._send_to_arduino(message)
                self.last_sent_message = message

        # ==============================
        # SCORING LOGIC
        # ==============================

        def _calculate_score(self, detected_label):

            expected_label = self.current_expected_label

            if detected_label == expected_label:
                return 100

            expected_class = self.current_expected_exercise_index
            detected_class = self._get_exercise_index_from_label(detected_label)

            if detected_class == expected_class:
                return 90

            if abs(detected_class - expected_class) == 1:
                return 50

            return 0

        def _get_exercise_index_from_label(self, label):
            for index, exercise in enumerate(self.WORKOUT_PLAN):
                for phase_name, _ in exercise["phases"]:
                    if phase_name == label:
                        return index
            return -1

        def _score_message(self, score):
            if score == 100:
                return "Perfect Form"
            elif score == 90:
                return "Wrong Phase"
            elif score == 50:
                return "Adjacent Exercise"
            else:
                return "Wrong Exercise"

        def _send_to_arduino(self, text):
            if self.arduino:
                try:
                    self.arduino.write((text + "\n").encode())
                except:
                    pass

        def send_final_report_to_arduino(self, report):
            if not self.arduino:
                return
            try:
                time.sleep(0.1)

                # START REPORT
                self.arduino.write(b"START_REPORT\n")
                time.sleep(0.05)

            # Final accuracy line
                final_line = f"Final Accuracy: {report['final_accuracy']:.2f}%\n"
                self.arduino.write(final_line.encode())
                time.sleep(0.05)

            # Exercise breakdown lines
                for ex in report["exercise_breakdown"]:
                    if ex["accuracy"] is None:
                        line = f"{ex['exercise']} : NA\n"
                    else:
                        line = f"{ex['exercise']} : {ex['accuracy']:.2f}%\n"

                    self.arduino.write(line.encode())
                    time.sleep(0.05)   # 50ms safe at 9600 baud

            # END REPORT
                self.arduino.write(b"END_REPORT\n")
                time.sleep(0.05)
            
            except Exception as e:
                print("Serial error:", e)