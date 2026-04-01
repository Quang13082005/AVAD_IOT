# Thuyết minh Toán học: Chuyển đổi Hệ tọa độ 2 Tháp lệch trục

Hệ thống **AVAD** bao gồm 2 tháp (Tower A và Tower B) đặt lệch nhau trong không gian 3 chiều. 
Việc bám đuổi yêu cầu xác định tọa độ $T(X, Y, Z)$ của mục tiêu từ tháp A (Camera), sau đó giải ngược góc ngắm cho tháp B (Laser).

## 1. Hệ Tọa Độ Gốc và Cấu Hình Cơ Khí
Điểm gốc $O(0, 0, 0)$ được đặt tại mặt đất, ngay chính giữa trục xoay (Pan) của Tháp A.
- Quy ước hướng: Trục $+Y$ hướng thẳng về phía trước (mặt định vị), trục $+X$ hướng sang phải, trục $+Z$ hướng lên trời.

**Tháp A (Camera):**
- Trục xoay Pan: $Z_{panA} = 41\text{cm}$
- Trục xoay Tilt (Quang tâm Camera): Đặt thêm $7\text{cm}$ lên trên, tổng $Z_A = 48\text{cm}$.
- Tâm quay quang học là điểm $C(0, 0, 48)$.

**Tháp B (Laser):**
- Đặt bên phải tháp A, cách một khoảng hướng $X$ là $17\text{cm}$.
- Chiều cao cọc: $Z_B = 6\text{cm}$.
- Tâm quay cụm Laser là điểm $L(17, 0, 6)$.

---

## 2. Ước lượng Chiều Sâu (Pinhole Model)
Camera chụp được một quả bóng màu cam (chuẩn đường kính thật $D_{real} = 4.0\text{cm}$).
Bằng YOLOv8, AI lấy ra được tham số chiều rộng Bounding Box $W_{pixel}$ trên ảnh (pixel).
Tỉ lệ tiêu cự $F$ (Focal length pixel) cố định của ống kính (vd: $f=500$ px).

Khoảng cách từ ống kính đến quả bóng được tính bằng định lý đồng dạng:
$$ R = \frac{F \times D_{real}}{W_{pixel}} $$

---

## 3. Forward Kinematics (FK) - Tháp A
Mục tiêu là tìm vị trí $T(X, Y, Z)$ của quả bóng thông qua thông số của tháp Camera: $Pan_A$, $Tilt_A$ và $R$.
- Giả sử biến $\phi$ là góc nâng (Elevation) so với mặt phẳng ngang: $\phi = Tilt_A - 90^{\circ}$
- Giả sử biến $\theta$ là góc tới (Azimuth) dọc theo trục $Y$: $\theta = Pan_A$ (với $0^{\circ}$ là trục $+Y$).

Áp dụng phương trình hình cầu:
- $X = R \cdot \cos(\phi) \cdot \sin(\theta)$
- $Y = R \cdot \cos(\phi) \cdot \cos(\theta)$
- $Z = Z_A + R \cdot \sin(\phi) = 48 + R \cdot \sin(\phi)$

---

## 4. Inverse Kinematics (IK) - Tháp B
Sau khi đã có $T(X, Y, Z)$, ta chuyển tọa độ này về hệ tọa độ cục bộ của Tháp B để tìm các góc $Pan_B, Tilt_B$.
Điểm lệch của Tháp B là $L(X_B, Y_B, Z_B) = (17, 0, 6)$.

Vector mục tiêu nhìn từ Tháp B: $\vec{V} = T - L$.
- $\Delta X = X - 17$
- $\Delta Y = Y - 0 = Y$
- $\Delta Z = Z - 6$

**Tính góc xoay phương vị (Pan B - $\theta_B$):**
Là góc hình chiếu của mục tiêu trên mặt phẳng X-Y so với trục Y.
$$ \theta_B = \text{atan2}(\Delta X, \Delta Y) \times \frac{180}{\pi} $$

**Tính góc nâng (Tilt B - $\phi_B$):**
Là góc nâng tương đối theo độ cao mục tiêu chia cho khoảng cách mặt phẳng.
$$ \text{Dist}_{xy} = \sqrt{\Delta X^2 + \Delta Y^2} $$
$$ \phi_{B} = \text{atan2}(\Delta Z, \text{Dist}_{xy}) \times \frac{180}{\pi} $$
Do Servo $Tilt_B$ 180 độ thường có mốc 90 là mặt ngang, ta cộng góc nâng $\phi_B$ với $90^{\circ}$ để gửi thẳng vào Servo:
$$ Tilt\_Command_B = 90 + \phi_B $$
