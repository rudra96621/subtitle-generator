import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import math

# -------------------- Initialization --------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

screen_w, screen_h = pyautogui.size()
cap = cv2.VideoCapture(0)

prev_x, prev_y = 0, 0
smooth_factor = 0.5

# -------------------- Blink / Click --------------------
blink_threshold = 0.25
last_left_click = 0
last_right_click = 0
click_delay = 0.5

# -------------------- Drag --------------------
dragging = False
drag_start_time = 0
drag_delay = 0.5  # seconds to start drag after blink

# Helper function
def euclidean(p1, p2):
    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])

print("👁 Eye-controlled mouse started — Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    gesture_name = "None"

    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]

        # --- Eye landmarks (MediaPipe indices for iris + corners) ---
        left_eye = [face.landmark[i] for i in [33, 133, 159, 145]]  # corner + iris
        right_eye = [face.landmark[i] for i in [263, 362, 386, 374]]

        # --- Iris center (normalized 0-1) ---
        left_iris_x = (left_eye[2].x + left_eye[3].x)/2
        left_iris_y = (left_eye[2].y + left_eye[3].y)/2

        # --- Map to screen coordinates ---
        target_x = int(left_iris_x * screen_w)
        target_y = int(left_iris_y * screen_h)

        # --- Smooth cursor ---
        dx = target_x - prev_x
        dy = target_y - prev_y
        if abs(dx) < 100 and abs(dy) < 100:
            x = int(prev_x + dx * smooth_factor)
            y = int(prev_y + dy * smooth_factor)
        else:
            x = target_x
            y = target_y
        prev_x, prev_y = x, y
        pyautogui.moveTo(x, y)

        # --- Blink detection ---
        left_eye_open = euclidean((left_eye[1].x, left_eye[1].y), (left_eye[3].x, left_eye[3].y))
        right_eye_open = euclidean((right_eye[1].x, right_eye[1].y), (right_eye[3].x, right_eye[3].y))

        current_time = time.time()
        blink_detected = left_eye_open < blink_threshold and right_eye_open < blink_threshold

        # --- LEFT CLICK: single blink ---
        if blink_detected and (current_time - last_left_click) > click_delay:
            pyautogui.click()
            last_left_click = current_time
            gesture_name = "LEFT CLICK"

        # --- DRAG: blink + hold eye closed ---
        if blink_detected and not dragging:
            drag_start_time = current_time
        if blink_detected and (current_time - drag_start_time) > drag_delay and not dragging:
            pyautogui.mouseDown()
            dragging = True
            gesture_name = "DRAG START"
        elif not blink_detected and dragging:
            pyautogui.mouseUp()
            dragging = False
            gesture_name = "DRAG END"

        # --- RIGHT CLICK: long blink (over 1 sec) ---
        if blink_detected and (current_time - last_right_click) > 1.0:
            pyautogui.click(button='right')
            last_right_click = current_time
            gesture_name = "RIGHT CLICK"

        # --- Optional: Scroll ---
        # Look up/down could be implemented by comparing iris_y to eye center

    # --- Display gesture on frame ---
    cv2.putText(frame, f"Gesture: {gesture_name}", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Eye-controlled Mouse", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
