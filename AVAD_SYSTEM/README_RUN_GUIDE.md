# Hướng Dẫn Chạy Dự Án Cài Đặt Hệ Thống AVAD (AI Vision Air Defense)

Để dự án hoạt động trơn tru toàn diện từ việc nhận diện AI trên PC cho tới điều khiển mạch ESP32-S3 bám mục tiêu thực tế, hãy làm theo tuần tự các bước dưới đây.

---

## Phần 1: Cài đặt và Nạp Firmware cho ESP32-S3 Cam

1. **Chuẩn bị Arduino IDE**:
   - Tải và cài đặt Arduino IDE bản mới nhất.
   - Thêm gói ESP32 board từ Espressif Systems vào phần `Preferences`.
   - Cài đặt thư viện **ESP32Servo** (bởi Kevin Harrington) thông qua `Library Manager`.

2. **Cấu hình Nạp Code (Flash)**:
   - Cắm cáp USB Type-C vào cổng kết nối của ESP32-S3 (Nhớ cắm vào mạch, không cắm vào nguồn rời).
   - Chọn Board: `ESP32S3 Dev Module`.
   - Trong Menu **Tools**:
     - Cài OPI PSRAM: `OPI PSRAM` (NẾU mạch bạn là WROVER, có ram ngoài).
     - Partition Scheme: `Huge APP (3MB No OTA...)` (Để vừa bộ nhớ Camera).
     - Bật Serial Monitor với chế độ `115200 baud`.
   
3. **Nạp Firmware**:
   - Mở tệp tin `e:\IOT\AVAD_SYSTEM\firmware\firmware.ino`.
   - Vui lòng sửa lại Thông tin mạng (SSID và Mật khẩu WiFi nhà bạn) trong Code.
   - Nhấn **Upload**. Lúc Upload chạy `Connecting...` nếu bị trễ, bạn có thể cần đè phím giữ nút `BOOT` trên mạch.
   - Khi chạy xong, bấm nút RESET trên mạch. 
   - Mở Serial Monitor và đón xem địa chỉ IP (Ví dụ: `192.168.1.168`) nhé! Không được tắt nguồn mạch.

---

## Phần 2: Cài Đặt Môi Trường Trí Tuệ Nhân Tạo (Phía Máy Tính)

Máy tính sẽ đứng vai trò xử lý tính toán toàn bộ não bộ của Hệ thống và bắt buộc cần Python.

1. **Cài Đặt Python và CUDA GPU**:
   - Máy tính cần cài đặt sẵn Python phiên bản `3.8 - 3.11`.
   - Mở Terminal (Command Prompt hoặc PowerShell).
   - Cài bộ thư viện Pytorch chuyên chịu tải phần cứng cho nhân card màn hình:
     ```bash
     pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
     ```
   
2. **Cài Đặt Các Thư Viện Hỗ Trợ Khác**:
   - Gõ lệnh sau vào Terminal:
     ```bash
     pip install ultralytics opencv-python numpy pyqt5 pyqtgraph
     ```

3. **Cập Nhật IP (Nếu Reset mạng)**:
   - Truy cập vào file lệnh `e:\IOT\AVAD_SYSTEM\ai_core\main_server.py`.
   - Thay đổi các biến chuỗi `"192.168.1.xxx"` ở lệnh `def __init__(...):` thành đúng thứ mà mạch ESP32 vừa in ra màn hình Serial lúc nãy.

---

## Phần 3: Chạy Thực Ngang Bằng Module Đồng Bộ Cơ Khí

Bạn cần cấp nguồn cho mạch hệ thống, đặc biệt nhớ bật mạch biến áp `5V/3A` nối vào Servo.

1. **Quy trình Calibration Khởi động (Bắt buộc)**:
   - Khi mạch ESP32 được cấp nguồn, bạn để nguyên hệ thống trong 5 giây. 
   - Các Servo sẽ xoay một góc nhỏ qua trái và phải rồi dừng yên cứng (Homing Sequence kết thúc).
   - *Đừng vội chạy Code Python vội!* Ngay lúc này, bạn lấy tuốc nơ vít, nới lỏng ốc ở bánh răng **Pan Laser (Tháp B)**.
   - Dùng tay cân chỉnh sao cho Tia Laser đang ngắm chĩa **SONG SONG GẦN NHẤT** dọc theo đường rọi ống kính Camera (Tháp A) - Hãy đảm bảo khoảng cách giữa 2 tâm cọc là đúng 17 cm.
   - Yếu tố này để lấy mốc "Góc O". Sau đó các bạn khóa chặt ốc lại. Máy đã sẵn sàng!

2. **Kích Hoạt Radar Trạm Giao Theo Dõi trên Máy Tính**:
   - Mở 2 Tab Terminal khác nhau trên Windows. Di chuyển cả 2 vào thư mục hệ thống:
     ```bash
     cd /d E:\IOT\AVAD_SYSTEM
     ```
   - **Tab Terminal 1 (Phòng điều khiển Bảng vẽ - Dashboard)**:
     ```bash
     python interface\dashboard.py
     ```
     Lúc này Dashboard đồ họa sẽ chạy lên, mở ra sóng Video thu từ hệ thống ESP32 và vạch sóng PID.

   - **Tab Terminal 2 (Não bộ AI Core)**:
     ```bash
     python ai_core\main_server.py
     ```
     Hệ thống bắt đầu download luồng Video trên ESP32. Nếu trên dòng Log bạn thấy hiện `Fusing layers...` thì tức là GPU chạy OKE.

---

## Phần 4: Vận Hành Thực Tiễn (Bắn Bám Bước Nhảy)
- Cầm một quả bóng bàn tiêu chuẩn (hoặc vật nhám hình cầu màu Cam gạch) đi ngang dọc trước mặt Camera ở khoảng cách từ 20cm - 3 MÉT.
- Nếu bạn thấy Box YOLO nhấp nháy khoanh quả bóng kèm đo tọa độ `T(x,y,z)` xanh lá cây.
- Lắng nghe Servo vặn tốc độ vù vù bám theo đồng bộ ở Tháp A và Tháp B bám sát vào giữa bóng!
- Có thể chuyển CheckBox trong Tab App PyQt5 giữa `Auto` và `Manual` để gỡ lỗi khi rớt mạng UDP.

**Q&A**:
> **Q**: Tại sao tốc độ tracking trên Camera theo sau vật thể rất rùa bò so với Frame Video?
> **A**: Tháp A dùng *Cascade PID* (Tăng $K_p$, Giảm $K_i$ trong `visual_servoing.py` của biến `self.pid_panA`). Chỉnh số lớn hơn để phản xạ gắt hơn (nhưng coi chừng quá lố sinh ra dao động rung lắc vỡ khung hình).

> **Q**: Tia Laser bám chậm hơn sự dự báo?
> **A**: Mặc định `Dead Reckoning` lấy góc đang bị sai số trôi giạt qua thời gian. Quét sai số theo biến đo chuẩn bằng lệnh `PWM_TO_DEG_SEC = 2.0` ở file `math_engine.py` (Có thể lên 3.0), tùy vào Torque mô men xoắn Servo của bạn.
