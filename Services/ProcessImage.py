import cv2
import mediapipe as mp
import numpy as np
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


class ProcessImage():

    def __init__(self):
        self.counter = 0
        self.stage = ""

    def calculate_angle(self, a, b, c):
        a = np.array(a)  # First
        b = np.array(b)  # Mid
        c = np.array(c)  # End

        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - \
            np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)

        # cy - by, cx-bx

        if angle > 180.0:
            angle = 360-angle

        return angle

    def process_frame(self, frame):

        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:

            # Recolor image to RGB
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            # Make detection
            results = pose.process(image)

            # Recolor back to BGR
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            # Extract landmarks
            try:
                landmarks = results.pose_landmarks.landmark

                # Get coordinates

                # 左跨部
                l_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]

                # 左膝蓋
                l_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                          landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]

                # 左腳踝
                l_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                           landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

                # 左腳跟
                l_heel = [landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x,
                          landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y]

                # 左腳前
                l_foot_index = [landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x,
                                landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y]

                # Calculate angle
                angle = self.calculate_angle(l_hip, l_knee, l_ankle)

                ankleAngle = self.calculate_angle(
                    l_knee, l_ankle, l_foot_index)

                # Visualize angle
                cv2.putText(image, str(angle),
                            tuple(np.multiply(l_knee, [640, 480]).astype(int)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,
                                                            255, 255), 2, cv2.LINE_AA
                            )

                # Visualize angle
                cv2.putText(image, str(ankleAngle),
                            tuple(np.multiply(l_heel, [640, 480]).astype(int)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,
                                                            255, 255), 2, cv2.LINE_AA
                            )

                # Curl counter logic
                if angle > 100:
                    self.stage = "d"
                if angle < 100 and self.stage == 'd':
                    self.stage = "up"
                    self.counter += 1

            except:
                pass

            # Render curl counter
            # Setup status box
            cv2.rectangle(image, (0, 0), (100, 73), (245, 117, 16), -1)

            # Rep data
            # cv2.putText(image, 'REPS', (15, 12),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(image, str(self.counter),
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

            # Stage data
            # cv2.putText(image, 'STAGE', (65, 12),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            # cv2.putText(image, self.stage,
            #             (60, 60),
            #             cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

            # Render detections
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                      mp_drawing.DrawingSpec(
                                          color=(245, 117, 66), thickness=2, circle_radius=2),
                                      mp_drawing.DrawingSpec(
                                          color=(245, 66, 230), thickness=2, circle_radius=2)
                                      )

        return [image, self.counter, self.stage]
