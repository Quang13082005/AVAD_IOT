import cv2
import socket
import time
import json
import threading
import urllib.request
import numpy as np
from struct import pack
from flask import Flask, Response
from detector import BallDetector
from tracker import TargetTracker
from math_engine import KinematicsEngine
from visual_servoing import ServoingEngine
# Global variable to hold the latest JPEG frame for Flask to serve
latest_jpeg_frame = None
app = Flask(__name__)
@app.route('/stream')
def video_feed():
    def generate():
        global latest_jpeg_frame
        while True:
            if latest_jpeg_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_jpeg_frame.tobytes() + b'\r\n')
            time.sleep(0.01) # Avoid 100% CPU lock
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
def start_flask_app():
    # Flask runs on port 5000 internally for Java GUI
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Disable verbose flask logs
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
class AVADServer:
    def __init__(self, esp_ip="192.168.1.225", udp_port=12345, stream_url="http://192.168.1.225:81/stream"):
        self.esp_ip = esp_ip
        self.udp_port = udp_port
        self.stream_url = stream_url
        
        # Ports for Java Relay
        self.java_ip = "127.0.0.1"
        self.java_udp_port = 12346
        
        # Modules
        print("Initializing AI Core Components...")
        self.detector = BallDetector(model_path='yolov8n.pt')
        self.tracker = TargetTracker()
        self.math_engine = KinematicsEngine()
        self.servoing = ServoingEngine(frame_size=(640, 480))
        
        # UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        
    def start(self):
        self.running = True
        
        # Start Flask background thread
        flask_thread = threading.Thread(target=start_flask_app, daemon=True)
        flask_thread.start()
        print("Flask MJPEG Server started at http://127.0.0.1:5000/stream")
        print(f"Opening MJPEG Stream from {self.stream_url} ...")
        
        try:
            stream = urllib.request.urlopen(self.stream_url, timeout=5)
            bytes_data = b''
        except Exception as e:
            print(f"Failed to open stream: {e}. Attempting local webcam (USB)...")
            # Fallback (Requires complete CV2 restructuring, but keeping it simple for now)
            print("Fallback to USB webcam is not supported in manual byte mode. Please check ESP32 connection.")
            return
        last_time = time.time()
        
        while self.running:
            # Read bytes until we get a full JPEG frame
            chunk = stream.read(4096)
            if not chunk:
                print("ESP32 closed the connection.")
                break
                
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8') # JPEG start
            b = bytes_data.find(b'\xff\xd9') # JPEG end
            
            if a == -1 or b == -1:
                continue
                
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is None:
                continue
                
            # Xoay khung hình để đưa camera về phương lập thể chuẩn (CLOCKWISE)
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            frame = cv2.resize(frame, (640, 480))
            
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            # --- AI PROCESSING ---
            bbox, center = self.detector.detect(frame)
            
            R = 0
            ix = 0
            iy = 0
            iz = 0
            
            if center is not None:
                R = self.math_engine.estimate_distance(bbox[2])
                
                panA_ang = self.math_engine.panA_current_angle
                tiltA_ang = self.math_engine.tiltA_current_angle
                px, py, pz = self.math_engine.forward_kinematics_camera(panA_ang, tiltA_ang, R)
                
                kf_pred = self.tracker.update([px, py, pz])
                ix, iy, iz = kf_pred
                
                fut_T = self.tracker.predict_future(0.05)
                ik_panB, ik_tiltB = self.math_engine.inverse_kinematics_laser(fut_T)
            else:
                self.tracker.reset()
                ik_panB, ik_tiltB = None, None
                
            # --- Visual Servoing Commands to ESP32 ---
            cmd_str, cmd_tup = self.servoing.calculate_commands(center, R, ik_panB, ik_tiltB, panA_angle=self.math_engine.panA_current_angle, panB_angle=self.math_engine.panB_current_angle)
            self.math_engine.update_dead_reckoning(cmd_tup[0], cmd_tup[1], cmd_tup[2], dt)
            self.sock.sendto(cmd_str.encode('utf-8'), (self.esp_ip, self.udp_port))
            
            # --- Sending MJPEG to Local Java GUI ---
            # We DONT draw on the frame. Java will do it. Just encode and broadcast the raw clean frame!
            global latest_jpeg_frame
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            success, buffer = cv2.imencode('.jpg', frame, encode_param)
            if success:
                latest_jpeg_frame = buffer
                
            # --- Sending Telemetry to Local Java GUI ---
            # Pack all AI data into a JSON structure
            telemetry = {
                "detected": center is not None,
                "box": {"x": bbox[0], "y": bbox[1], "w": bbox[2], "h": bbox[3]} if bbox else None,
                "center": {"x": center[0], "y": center[1]} if center else None,
                "coords": {"x": round(ix,2), "y": round(iy,2), "z": round(iz,2)},
                "distance": round(R, 2),
                "camera": {"pan": round(self.math_engine.panA_current_angle, 2), "tilt": round(self.math_engine.tiltA_current_angle, 2)},
                "laser": {"pan": round(ik_panB, 2) if ik_panB else 0, "tilt": round(ik_tiltB, 2) if ik_tiltB else 0},
                "server_fps": round(1.0/dt if dt > 0 else 0, 1)
            }
            json_payload = json.dumps(telemetry)
            self.sock.sendto(json_payload.encode('utf-8'), (self.java_ip, self.java_udp_port))
            
            # We no longer use cv2.imshow here to free up Python's rendering thread and save pure CPU cycles. 
            # If the user wants to debug, they open the Java Window!
            
        self.sock.close()
if __name__ == "__main__":
    server = AVADServer()
    server.start()
