import numpy as np

class TargetTracker:
    def __init__(self, dt=0.033): # default 30 fps
        self.dt = dt
        # State: [X, Y, Z, Vx, Vy, Vz]
        self.state = np.zeros(6)
        
        # State Transition Matrix
        self.F = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1,  0, 0],
            [0, 0, 0, 0,  1, 0],
            [0, 0, 0, 0,  0, 1]
        ])
        
        # Measurement Matrix (We measure X, Y, Z directly after FK)
        self.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        
        # Covariance Matrix
        self.P = np.eye(6) * 1000.0
        
        # Measurement Noise Covariance
        self.R = np.eye(3) * 10.0 # Standard deviation of measurement
        
        # Process Noise Covariance
        self.Q = np.eye(6) * 0.1
        
        self.initialized = False
        
    def predict(self):
        if not self.initialized:
            return np.zeros(3)
            
        self.state = self.F @ self.state
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.state[:3]
        
    def update(self, measurement):
        if not self.initialized:
            self.state[:3] = measurement
            self.state[3:] = 0
            self.initialized = True
            return measurement
            
        Z = np.array(measurement)
        Y = Z - (self.H @ self.state)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        self.state = self.state + K @ Y
        self.P = (np.eye(6) - K @ self.H) @ self.P
        
        return self.state[:3]
        
    def predict_future(self, latency_seconds):
        """Predict where the target will be X seconds in the future"""
        if not self.initialized:
            return np.zeros(3)
        future_state = self.state.copy()
        temp_F = np.array([
            [1, 0, 0, latency_seconds, 0, 0],
            [0, 1, 0, 0, latency_seconds, 0],
            [0, 0, 1, 0, 0, latency_seconds],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        future_state = temp_F @ future_state
        return future_state[:3]

    def reset(self):
        """Xóa sạch bộ nhớ dự đoán quỹ đạo khi không thấy mục tiêu"""
        self.initialized = False
        self.state = np.zeros(6)
