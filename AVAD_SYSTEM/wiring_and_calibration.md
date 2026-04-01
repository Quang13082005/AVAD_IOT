# Sơ đồ Đấu dây (Wiring Diagram) & Hiệu chuẩn (Calibration) AVAD

## 1. Sơ đồ Đấu Dây Chi Tiết (ESP32-S3 Camera)

Hệ thống hoạt động với phân ban nguồn riêng biệt cho vi điều khiển tính toán (ESP32) và tải động cơ (Servo). **Dùng chung Mass (GND) là bắt buộc.**

### 1.1 Khối Nguồn (Power Delivery)
- **Nguồn cấp mạch Servo**: Nguồn tổ ong/Mạch HW-131 (Cấp `5V` và `3A - 5A`).
  - `VCC (5V)` -> Chân giữa (Đỏ) của toàn bộ 4 Servo.
  - `GND (Mass)` -> Chân cực (Nâu) của toàn bộ 4 Servo.
  - **Dây Link**: Kéo 1 dây cáp từ `GND` của mạch HW-131 nối vào chân `GND` của bo mạch ESP32.
- **Nguồn cấp ESP32**: Nguồn cổng USB Máy tính hoặc sạc dự phòng 5V qua cáp USB Type-C.

### 1.2 Khối Mạch Tín Hiệu (GPIO Signal)
- Cáp Tín hiệu của Servo (Màu Cam / Trắng / Vàng):
  - **Tower A (Camera)**: 
    - Dây cam `Pan A` (Servo 360) nết nối với Pin `GPIO 39` của ESP32.
    - Dây cam `Tilt A` (Servo 180) nối với Pin `GPIO 40` của ESP32.
  - **Tower B (Laser)**:
    - Dây cam `Pan B` (Servo 360) nối với Pin `GPIO 41` của ESP32.
    - Dây cam `Tilt B` (Servo 180) nối với Pin `GPIO 42` của ESP32.

> Vị trí các chân từ Pin 39 -> 42 là những chân Input-Output rảnh trên ESP32-S3 không bị trùng lặp với Cụm Camera. Cẩn thận không cắm nhầm vì các chân khác sẽ làm nhiễu Camera PWDN.

---

## 2. Hướng dẫn Hiệu Chuẩn (Calibration) Đồng bộ Laser

Vì Servo 360 của bạn **không có Encoder đọc góc**, sau khi cấp điện lần đầu tiên, hệ thống không biết Laser và Camera đang quay về hướng nào so với mặt phẳng O(0,0,0). Quy trình sau gọi là "Homing" hoặc Calibration ban đầu.

### **Bước 1: Cơ Khí Điện Ban Đầu**
- Khởi động hệ thống AVAD (Firmware ESP32 boot lên, sau đó bật File `main_server.py`).
- Hàm Setup trong Camera lúc này sẽ điều khiển tất cả `Tilt = 90 độ` và `Pan = 90 (Dừng)`.
- Lúc này, Servo sẽ ghim chặt (ứng lực cứng) không cho vặn tay trục nâng hạ (Tilt). 

### **Bước 2: Căn Gióng Bằng Tay (Manual Alignment)**
- Nhấc hoặc xoay khay Base/Đế của Camera (Chỉnh nguyên tháp xoay bằng tay) sao cho Camera nhìn đúng chuẩn theo trục +Y của phòng (Tia thẳng về phía trước theo hướng mắt mình).
- Nhấc cụm tháp Laser (Tháp B), đặt nó song song với tháp A, căn sao cho khoảng cách giữa tâm cột A và tâm cột B là đúng `17cm` (như trong tham số `math_engine`).
- Dùng tua-vít nới lỏng trục rẽ quạt của Pan A và Pan B, vặn cho cọc Laser hướng thẳng song song với Camera, rồi vặn cứng ốc lại.

### **Bước 3: Tinh chỉnh Laser trên Dashboard**
- Nối nguồn cho Laser 5V chiếu tia sáng vào tường.
- Bật Dashboard trên PyQt5. Chuyển sang chế độ Manual. 
- Mở một vật thể (VD: quả bóng bàn thật) đặt ngay trước tia Laser (để hiện chấm đỏ trên quả bóng).
- Quan sát luồng hình ảnh Camera trả về. Click vào quả bóng trong màn hình hiển thị bằng chuột hoặc các thanh kéo (nếu lập trình thêm) cho đến khi Laser đậu chính xác vào trung tâm Camera.
- Lúc này, Hệ thống Toán học `math_engine` sẽ khóa góc lệch `Dead Reckoning = 0`, đánh dấu điểm `Homing`.

### **Bước 4: Xác Nhận & Auto Tracking**
- Khi quả bóng di chuyển nhẹ, quan sát xem Laser phản ứng Inverse Kinematics đúng chuẩn chưa. Nếu tia bị trượt ngang: Có thể khoảng cách đo $R$ sai (Sửa `REAL_BALL_DIA` trong code AI) hoặc offset $17cm$ không chính xác.
- Khi tín hiệu mượt mà, chuyển sang nút `Auto (AI Tracking)`.
