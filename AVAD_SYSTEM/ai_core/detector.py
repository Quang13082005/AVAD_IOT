import cv2
from ultralytics import YOLO
class BallDetector:
    def __init__(self, model_path='yolov8n.pt', classes=[32]): 
        # class 32 is 'sports ball' in COCO. 
        # In a real scenario, a custom model trained on 'orange ping pong ball' would be better.
        # Ensure you export to TensorRT (.engine) for best latency: yolo export model=yolov8n.pt format=engine device=0
        print(f"Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        self.classes = classes
        
    def detect(self, frame):
        best_box = None
        best_center = None
        largest_area = 0
        
        # --- BỘ LỌC TỐC ĐỘ CAO (PURE OPENCV FAST-TRACK) ---
        # Ưu tiên chạy bộ lọc màu và hình học siêu nhẹ trước. Mất xấp xỉ 1ms/frame!
        # Điều này giúp tăng tốc FPS lên tối đa (30-60FPS) mượt mà không độ trễ.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 100, 100), (28, 255, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 100: # Bỏ qua nhiễu
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = w / float(h)
                
                if 0.6 < aspect_ratio < 1.4: # Ước lượng hình vuông bao tròn
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter == 0: continue
                    circularity = 4 * 3.14159 * (area / (perimeter * perimeter))
                    
                    if circularity > 0.55: # Chỉ số càng gần 1 càng xoe tròn
                        if area > largest_area:
                            largest_area = area
                            best_box = (x, y, w, h)
                            best_center = (int(x + w/2), int(y + h/2))
                            
        # --- MẠNG NƠ RON THẦN KINH DỰ PHÒNG (YOLO FALLBACK) ---
        # Nếu bộ lọc siêu tốc không thấy bóng, YOLO sẽ rà quét chậm để cố lấy lại dấu vết.
        if best_box is None:
            # Run inference: lower res (imgsz=320) for SPEED.
            results = self.model.predict(source=frame, classes=None, imgsz=320, conf=0.5, verbose=False, device=0)
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    roi = frame[y1:y2, x1:x2]
                    if roi.size == 0: continue
                    
                    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    mask_roi = cv2.inRange(hsv_roi, (0, 80, 80), (30, 255, 255))
                    orange_pixels = cv2.countNonZero(mask_roi)
                    total_pixels = roi.shape[0] * roi.shape[1]
                    
                    if orange_pixels / total_pixels > 0.15:
                        w = x2 - x1
                        h = y2 - y1
                        aspect_ratio = w / float(h)
                        
                        if 0.60 < aspect_ratio < 1.40: 
                            area = w * h
                            if area > largest_area:
                                largest_area = area
                                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                                best_box = (x1, y1, w, h)
                                best_center = (cx, cy)
                                
        return best_box, best_center
