import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading

class NeuralActivityVisualizer:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        
        # Initialize data
        self.x_data = np.linspace(0, 10, 200)
        self.y_data = np.zeros(200)
        self.state = 'idle'  # 'speaking', 'thinking', 'idle', 'listening'
        self.time_offset = 0
        self.lock = threading.Lock()
        
        # Create line
        self.line, = self.ax.plot(self.x_data, self.y_data, 'gray', linewidth=2)
        
        # Set up plot
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(-2, 2)
        self.ax.set_xlabel('Time', fontsize=12)
        self.ax.set_ylabel('Neural Response', fontsize=12)
        self.ax.set_title('Neural Activity Visualization - Current State: IDLE', 
                         fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        
        # Animation
        self.ani = FuncAnimation(self.fig, self.update, interval=50, blit=False)
        
    def speaking(self):
        """Activate speaking state - moderate wave pattern"""
        with self.lock:
            self.state = 'speaking'
            self.ax.set_title('Neural Activity Visualization - Current State: SPEAKING', 
                             fontsize=14, fontweight='bold')
            self.line.set_color('blue')
        print("State changed to: SPEAKING")
    
    def listening(self):
        """Activate listening state - attentive, responsive pattern"""
        with self.lock:
            self.state = 'listening'
            self.ax.set_title('Neural Activity Visualization - Current State: LISTENING', 
                             fontsize=14, fontweight='bold')
            self.line.set_color('purple')
        print("State changed to: LISTENING")
        
    def thinking(self):
        """Activate thinking state - high amplitude erratic pattern"""
        with self.lock:
            self.state = 'thinking'
            self.ax.set_title('Neural Activity Visualization - Current State: THINKING', 
                             fontsize=14, fontweight='bold')
            self.line.set_color('green')
        print("State changed to: THINKING")
        
    def idle(self):
        """Activate idle state - minimal activity"""
        with self.lock:
            self.state = 'idle'
            self.ax.set_title('Neural Activity Visualization - Current State: IDLE', 
                             fontsize=14, fontweight='bold')
            self.line.set_color('gray')
        print("State changed to: IDLE")
        
    def generate_wave(self, t):
        with self.lock:
            current_state = self.state
            
        if current_state == 'speaking':
            # Moderate, consistent wave pattern (user speaking)
            wave = 0.5 * np.sin(2 * np.pi * 0.8 * t) + \
                   0.2 * np.sin(2 * np.pi * 1.5 * t) + \
                   0.1 * np.random.randn(len(t))
        
        elif current_state == 'listening':
            # Attentive, steady pattern with slight variations (actively listening)
            wave = 0.35 * np.sin(2 * np.pi * 1.0 * t) + \
                   0.25 * np.sin(2 * np.pi * 2.0 * t) + \
                   0.15 * np.sin(2 * np.pi * 3.0 * t) + \
                   0.08 * np.random.randn(len(t))
                   
        elif current_state == 'thinking':
            # High amplitude, erratic pattern (brain processing)
            wave = 0.8 * np.sin(2 * np.pi * 1.2 * t) + \
                   0.6 * np.sin(2 * np.pi * 2.3 * t) + \
                   0.4 * np.sin(2 * np.pi * 3.5 * t) + \
                   0.3 * np.random.randn(len(t))
                   
        else:  # idle
            # Minimal, flat activity
            wave = 0.1 * np.sin(2 * np.pi * 0.3 * t) + \
                   0.05 * np.random.randn(len(t))
        
        return wave
    
    def update(self, frame):
        self.time_offset += 0.1
        t = self.x_data + self.time_offset
        self.y_data = self.generate_wave(t)
        self.line.set_ydata(self.y_data)
        return self.line,
    
    def show(self):
        """Display the visualization"""
        plt.show()
