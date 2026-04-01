import time
class PIDController:
    def __init__(self, kp, ki, kd, output_limits=(-50, 50)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.limits = output_limits
        
        self.integral = 0
        self.prev_error = 0
        self.last_time = time.time()
        
    def compute(self, error):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0.0:
            dt = 0.001
            
        proportional = error * self.kp
        self.integral += error * dt * self.ki
        derivative = (error - self.prev_error) / dt * self.kd
        
        output = proportional + self.integral + derivative
        
        # Clamp output
        output = max(self.limits[0], min(self.limits[1], output))
        
        self.prev_error = error
        self.last_time = current_time
        
        return output
class ServoingEngine:
    def __init__(self, frame_size=(640, 480)):
        self.cx = frame_size[0] // 2
        self.cy = frame_size[1] // 2
        
        # PIDs for Image Based Visual Servoing (Camera A)
        self.pid_panA = PIDController(kp=0.08, ki=0.005, kd=0.03, output_limits=(-20, 20))
        self.pid_tiltA = PIDController(kp=0.06, ki=0.002, kd=0.02, output_limits=(-8, 8))
        
        # PIDs for Pure Position-Velocity Servoing (Laser B)
        self.pid_panB = PIDController(kp=0.1, ki=0.0, kd=0.02, output_limits=(-20, 20))
        
        self.cur_tiltA = 90.0
        
    def calculate_commands(self, target_center, target_R, ik_panB, ik_tiltB, panA_angle=0.0, panB_angle=0.0):
        """
        Calculates the command string to send to the ESP32.
        - target_center: (x, y) pixel coordinates of the ball.
        - ik_panB: The absolute calculated angle for laser Pan (needs to be converted to speed for 360 servo)
        - ik_tiltB: The absolute calculated angle for laser Tilt (180 servo)
        - panA_angle: Current dead-reckoning angle of the camera pan for safety limits.
        - panB_angle: Current dead-reckoning angle of the laser pan.
        
        Returns a formatted string: "panA_speed,tiltA_pos,panB_speed,tiltB_pos"
        """
        # --- CẤU HÌNH CÂN BẰNG ĐỘNG CƠ (STOP POINT) ---
        PAN_STOP_PWM = 90
        
        # --- HƯỚNG DẪN CĂN CHỈNH CHIỀU QUAY ---
        REVERSE_PAN_DIRECTION_A = False  # CAMERA XY ngang
        REVERSE_TILT_DIRECTION_A = False # CAMERA Lên Xuống
        REVERSE_PAN_DIRECTION_B = False  # LAZER chiều ngang
        
        # --- Camera Servo A Control ---
        if target_center is None:
            # Stop tracking
            cmd_panA = PAN_STOP_PWM
            cmd_tiltA = int(self.cur_tiltA)
        else:
            err_x = target_center[0] - self.cx
            err_y = target_center[1] - self.cy # Nếu bóng ở dưới, err_y > 0
            
            # Pan A is a 360 Servo (Speed control). 90 is stop.
            speed_pan = self.pid_panA.compute(err_x)
            if REVERSE_PAN_DIRECTION_A:
                speed_pan = -speed_pan
                
            # === Bù Vùng Lì Cơ Học (Deadband) === 
            if speed_pan > 0.5:
                speed_pan += 6
            elif speed_pan < -0.5:
                speed_pan -= 6
                
            cmd_panA = int(PAN_STOP_PWM + speed_pan)
            
            # --- GIỚI HẠN GÓC QUAY 180 ĐỘ TRÁNH ĐỨT DÂY ---
            if panA_angle > 170 and cmd_panA > PAN_STOP_PWM:
                cmd_panA = PAN_STOP_PWM # Khóa chết ngàm phải, tránh đứt dây
            elif panA_angle < -170 and cmd_panA < PAN_STOP_PWM:
                cmd_panA = PAN_STOP_PWM # Khóa chết ngàm trái, tránh đứt dây
            
            # Tilt A is a 180 Servo (Position control).
            pos_tilt = self.pid_tiltA.compute(err_y)
            if REVERSE_TILT_DIRECTION_A:
                pos_tilt = -pos_tilt
                
            self.cur_tiltA = max(0, min(180, self.cur_tiltA - pos_tilt))
            cmd_tiltA = int(self.cur_tiltA)
            
        # --- Laser Servo B Control ---
        if target_center is None or ik_panB is None:
            cmd_panB = PAN_STOP_PWM
            cmd_tiltB = 90
        else:
            # Tính toán độ chênh lệch Góc Cần Tới (ik_panB) và Góc Hiện Tại (panB_angle)
            err_panB = ik_panB - panB_angle
            
            # Nếu chênh lệch > 180 thì đi đường tắt ngược lại
            if err_panB > 180: err_panB -= 360
            if err_panB < -180: err_panB += 360
            
            speed_panB = self.pid_panB.compute(err_panB)
            if REVERSE_PAN_DIRECTION_B:
                speed_panB = -speed_panB
                
            # Bù Lì Cơ Học cho Tháp Lazer
            if speed_panB > 1.0: speed_panB += 6
            elif speed_panB < -1.0: speed_panB -= 6
                
            cmd_panB = int(PAN_STOP_PWM + speed_panB)
            
            # --- Giới hạn 180 độ cho Lazer ---
            if panB_angle > 170 and cmd_panB > PAN_STOP_PWM:
                cmd_panB = PAN_STOP_PWM
            elif panB_angle < -170 and cmd_panB < PAN_STOP_PWM:
                cmd_panB = PAN_STOP_PWM
                
            # Trục dọc Lazer (Tilt B)
            cmd_tiltB = int(max(0, min(180, ik_tiltB)))
            
        # Format for UDP
        cmd_str = f"{cmd_panA},{cmd_tiltA},{cmd_panB},{cmd_tiltB}"
        return cmd_str, (cmd_panA, cmd_tiltA, cmd_panB, cmd_tiltB)
