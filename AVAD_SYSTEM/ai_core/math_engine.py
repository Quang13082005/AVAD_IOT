import numpy as np
class KinematicsEngine:
    def __init__(self):
        # Constants from Mechanical Specs
        self.ZA = 48.0  # Camera tilt axis height (cm)
        self.ZB = 6.0   # Laser tilt axis height (cm)
        self.XB = 17.0  # X offset of tower B (cm)
        self.YB = 0.0   # Y offset of tower B (cm)
        
        # Pinhole Camera Model (Assuming 640x480 resolution, 50 deg FOV approx)
        self.FOCAL_LENGTH = 500  # pixels
        self.REAL_BALL_DIA = 4.0 # 40mm ping pong ball = 4.0 cm
        
        # Current State Tracking (Dead Reckoning)
        self.panA_current_angle = 0.0
        self.tiltA_current_angle = 90.0 # Straight ahead (90 degree)
        
        self.panB_current_angle = 0.0
        self.tiltB_current_angle = 90.0
    def estimate_distance(self, bbox_width):
        """
        Estimate distance R from camera to target using Pinhole Camera Model
        R = (Focal_Length * Real_Object_Width) / Pixel_Width
        """
        if bbox_width == 0:
            return 0
        return (self.FOCAL_LENGTH * self.REAL_BALL_DIA) / bbox_width
    def forward_kinematics_camera(self, pan_angle, tilt_angle, R):
        """
        Convert PanA, TiltA, R into T(X, Y, Z).
        Origin O(0,0,0) is base of Tower A.
        Assuming Pan=0 means looking at Y axis. Positive Pan goes to +X right?
        Let's assume Pan=0 is along +Y, Pan=90 is +X. Tilt=90 is horizontal.
        Standard spherical -> X = R * cos(tilt) * sin(pan), Y = R * cos(tilt) * cos(pan), Z = ZA + R * sin(tilt)
        Let's use a simplified version.
        Suppose Tilt = 90 is horizontal.
        phi = np.radians(tilt_angle - 90)  # Elevation angle from horizontal. Positive means up.
        theta = np.radians(pan_angle)      # Azimuth from Y axis
        """
        phi = np.radians(tilt_angle - 90) # Elevation, positive if looking UP
        theta = np.radians(pan_angle)     # Azimuth, positive if looking RIGHT
        
        X = R * np.cos(phi) * np.sin(theta)
        Y = R * np.cos(phi) * np.cos(theta)
        Z = self.ZA + R * np.sin(phi)
        
        return X, Y, Z
        
    def inverse_kinematics_laser(self, T_coords):
        """
        Calculates angles for PanB and TiltB given Target(X, Y, Z)
        Returns pan_angle, tilt_angle
        """
        if T_coords is None:
            return None, None
            
        TX, TY, TZ = T_coords
        
        # Calculate Delta from Tower B
        dX = TX - self.XB
        dY = TY - self.YB
        dZ = TZ - self.ZB
        
        # Pan B (theta_B)
        # Azimuth from Y axis. tan(theta) = dX / dY
        pan_rad = np.arctan2(dX, dY)
        pan_deg = np.degrees(pan_rad)
        
        # Tilt B (phi_B)
        # Elevation from horizontal
        xy_dist = np.sqrt(dX**2 + dY**2)
        tilt_rad = np.arctan2(dZ, xy_dist)
        tilt_deg = np.degrees(tilt_rad) + 90 # Add 90 because 90 is horizontal
        
        return pan_deg, tilt_deg
        
    def update_dead_reckoning(self, pan_speed_cmd, tilt_pos_cmd, panB_speed_cmd, dt):
        """
        Updates the internal state based on the commands sent.
        speed_cmd: 0-180 (PAN_STOP_PWM stops). 
        Need to calibrate how many degrees per second each PWM offset means.
        """
        PWM_TO_DEG_SEC = 2.0 # Assume 1 unit offset from 90 = 2 deg/sec rotation. Needs calibration!
        
        # --- CẬP NHẬT PAN A (CAMERA) ---
        speed_A = (pan_speed_cmd - 90) * PWM_TO_DEG_SEC
        self.panA_current_angle += speed_A * dt
        # Chốt cứng góc xoay ước tính trong khoảng -180 đến +180 độ
        self.panA_current_angle = max(-180.0, min(180.0, self.panA_current_angle))
            
        self.tiltA_current_angle = tilt_pos_cmd
        
        # --- CẬP NHẬT PAN B (LAZER) ---
        speed_B = (panB_speed_cmd - 90) * PWM_TO_DEG_SEC
        self.panB_current_angle += speed_B * dt
        self.panB_current_angle = max(-180.0, min(180.0, self.panB_current_angle))