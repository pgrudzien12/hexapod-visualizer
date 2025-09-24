#!/usr/bin/env python3
"""
Hexapod Visualizer Demo Mode
Demonstrates the 3D visualization with simulated hexapod movement patterns.
Useful for testing the visualization without a connected robot.
"""

import numpy as np
import time
import math
import threading
from typing import Optional

from visualizer import HexapodVisualizer, HexapodState
from main import LegData
from config_loader import ConfigLoader, LegConfiguration


class HexapodDemo:
    """Demo simulator for hexapod movement patterns."""
    
    def __init__(self, config):
        self.config = config
        self.running = False
        self.demo_thread = None
        self.visualizer = None
        
        # Demo parameters
        self.step_height = 0.05  # How high legs lift during walking
        self.step_length = 0.08  # Forward step distance
        self.body_height = 0.28  # Default body height above ground
        self.gait_speed = 2.0    # Cycles per second
        
    def _simulate_tripod_gait(self):
        """Simulate a tripod gait pattern."""
        print("Starting tripod gait simulation...")
        
        # Tripod groups: [0,2,4] and [1,3,5]
        group_a = [0, 2, 4]  # Left front, left back, right middle
        group_b = [1, 3, 5]  # Left middle, right front, right back
        
        start_time = time.time()
        
        while self.running:
            current_time = time.time() - start_time
            
            # Calculate gait phase (0-1)
            gait_phase = (current_time * self.gait_speed) % 1.0
            
            for leg_id in range(6):
                leg_config = self.config.get_leg_config(leg_id)
                
                # Determine which group this leg belongs to
                is_group_a = leg_id in group_a
                
                # Phase offset for the two groups
                phase = gait_phase if is_group_a else (gait_phase + 0.5) % 1.0
                
                # Calculate leg position
                if phase < 0.5:
                    # Stance phase - leg is on ground moving backward relative to body
                    ground_progress = phase / 0.5  # 0 to 1
                    forward_offset = self.step_length * (0.5 - ground_progress)
                    height_offset = 0.0
                else:
                    # Swing phase - leg is in air moving forward relative to body  
                    air_progress = (phase - 0.5) / 0.5  # 0 to 1
                    forward_offset = self.step_length * (air_progress - 0.5)
                    # Parabolic height profile
                    height_offset = self.step_height * 4 * air_progress * (1 - air_progress)
                
                # Calculate position in body coordinates
                base_x, base_y, base_z = leg_config.position
                
                # Apply forward offset in the direction of leg rotation
                cos_rot = math.cos(leg_config.rotation)
                sin_rot = math.sin(leg_config.rotation)
                
                body_x = base_x + forward_offset * cos_rot
                body_y = base_y + forward_offset * sin_rot
                body_z = -self.body_height + height_offset
                
                # Create fake leg data
                fake_timestamp = int(current_time * 1_000_000)  # Convert to microseconds
                
                leg_data = LegData(
                    leg_number=leg_id,
                    timestamp=fake_timestamp,
                    body_xyz=(body_x, body_y, body_z),
                    leg_xyz=(0.23, 0.0, body_z),  # Simplified leg coordinates
                    leg_angles=(0.0, math.atan2(-body_z, 0.23), 0.8),  # Simplified angles
                    leg_config=leg_config
                )
                
                # Send to visualizer
                if self.visualizer:
                    try:
                        self.visualizer.data_queue.put_nowait(leg_data)
                    except:
                        pass  # Queue full, skip this update
            
            # Control update rate
            time.sleep(1.0 / 60.0)  # 60 Hz updates
    
    def _simulate_wave_pattern(self):
        """Simulate a wave-like movement pattern."""
        print("Starting wave pattern simulation...")
        
        start_time = time.time()
        
        while self.running:
            current_time = time.time() - start_time
            
            for leg_id in range(6):
                leg_config = self.config.get_leg_config(leg_id)
                base_x, base_y, base_z = leg_config.position
                
                # Create wave motion
                wave_phase = current_time * 2.0 + leg_id * math.pi / 3
                
                # Vertical wave
                height_offset = self.step_height * 0.5 * (1 + math.sin(wave_phase))
                
                # Radial wave
                radius_offset = 0.02 * math.sin(wave_phase * 1.5)
                cos_rot = math.cos(leg_config.rotation)
                sin_rot = math.sin(leg_config.rotation)
                
                body_x = base_x + radius_offset * cos_rot
                body_y = base_y + radius_offset * sin_rot
                body_z = -self.body_height + height_offset
                
                # Create fake leg data
                fake_timestamp = int(current_time * 1_000_000)
                
                leg_data = LegData(
                    leg_number=leg_id,
                    timestamp=fake_timestamp,
                    body_xyz=(body_x, body_y, body_z),
                    leg_xyz=(0.23, 0.0, body_z),
                    leg_angles=(0.0, math.atan2(-body_z, 0.23), 0.8),
                    leg_config=leg_config
                )
                
                # Send to visualizer
                if self.visualizer:
                    try:
                        self.visualizer.data_queue.put_nowait(leg_data)
                    except:
                        pass
            
            time.sleep(1.0 / 60.0)
    
    def start_demo(self, pattern: str = "tripod"):
        """Start the demo simulation."""
        self.running = True
        
        # Choose simulation pattern
        if pattern == "tripod":
            target_func = self._simulate_tripod_gait
        elif pattern == "wave":
            target_func = self._simulate_wave_pattern
        else:
            print(f"Unknown pattern: {pattern}. Using tripod.")
            target_func = self._simulate_tripod_gait
        
        # Start demo thread
        self.demo_thread = threading.Thread(target=target_func, daemon=True)
        self.demo_thread.start()
    
    def stop_demo(self):
        """Stop the demo simulation."""
        self.running = False
        if self.demo_thread:
            self.demo_thread.join(timeout=1.0)


class DemoVisualizer(HexapodVisualizer):
    """Modified visualizer that doesn't connect to serial port."""
    
    def _serial_reader_thread(self):
        """Override to disable serial reading."""
        print("Demo mode - no serial connection")
        
        while self.running:
            time.sleep(0.1)  # Just wait, data comes from demo simulator


def main():
    """Main entry point for demo mode."""
    print("Hexapod 3D Visualizer - DEMO MODE")
    print("Loading configuration...")
    
    try:
        # Load configuration
        config = ConfigLoader.load_config("config.yaml")
        print(f"✓ Configuration loaded successfully!")
        
        # Create demo simulator and visualizer
        demo = HexapodDemo(config)
        visualizer = DemoVisualizer(config)
        
        # Link them together
        demo.visualizer = visualizer
        
        # Ask user for demo pattern
        print("\nAvailable demo patterns:")
        print("1. tripod - Tripod gait walking pattern")
        print("2. wave   - Wave-like movement pattern")
        
        choice = input("Select pattern (1-2) or press Enter for tripod: ").strip()
        
        if choice == "2":
            pattern = "wave"
        else:
            pattern = "tripod"
        
        print(f"Starting {pattern} pattern demo...")
        
        # Start demo
        demo.start_demo(pattern)
        
        print("Starting 3D visualization...")
        print("Close the plot window to exit.")
        
        # Start visualization
        visualizer.start_visualization()
        
        # Cleanup
        demo.stop_demo()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())