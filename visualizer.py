#!/usr/bin/env python3
"""
Hexapod 3D Visualizer
Real-time 3D visualization of hexapod robot kinematics data.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import queue
import time
import math
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field

from main import SerialReader, LegData
from config_loader import ConfigLoader, HexapodConfig


@dataclass
class HexapodState:
    """Current state of the hexapod robot."""
    timestamp: float = 0.0
    leg_positions: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)  # Body coordinates
    leg_targets: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)   # Leg coordinates
    leg_angles: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)    # Servo angles
    
    def update_leg(self, leg_data: LegData):
        """Update state with new leg data."""
        self.timestamp = time.time()
        self.leg_positions[leg_data.leg_number] = leg_data.body_xyz
        self.leg_targets[leg_data.leg_number] = leg_data.leg_xyz
        self.leg_angles[leg_data.leg_number] = leg_data.leg_angles


class HexapodVisualizer:
    """3D visualizer for hexapod robot using matplotlib."""
    
    def __init__(self, config: HexapodConfig):
        self.config = config
        self.state = HexapodState()
        self.data_queue = queue.Queue(maxsize=100)
        
        # Performance tracking
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        self.data_rate = 0.0
        self.last_data_count = 0
        self.last_data_time = time.time()
        
        # Visualization settings
        self.update_rate = config.visualization.update_rate
        self.show_body = config.visualization.show_body
        self.show_legs = config.visualization.show_legs
        self.show_coordinates = config.visualization.show_coordinates
        
        # Colors (convert from RGB 0-255 to 0-1)
        colors = config.visualization.colors
        self.body_color = [c/255.0 for c in colors["body"]]
        self.leg_color = [c/255.0 for c in colors["legs"]]
        self.coord_color = [c/255.0 for c in colors["coordinates"]]
        self.joint_color = [c/255.0 for c in colors.get("joints", [255,215,0])]
        
        # Initialize matplotlib figure and 3D axes
        self.fig = plt.figure(figsize=(12, 9))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Set up the plot
        self._setup_plot()
        
        # Plot elements that will be updated
        self.body_lines = []
        self.leg_lines = []
        self.leg_points = []
        self.coord_lines = []
        self.joint_lines = []
        self.joint_points = []
        self.joint_texts = []
        
        # Threading
        self.serial_thread = None
        self.running = False
        
    def _setup_plot(self):
        """Configure the 3D plot appearance and limits."""
        self.ax.set_xlabel('X (m) - Forward')
        self.ax.set_ylabel('Y (m) - Left')
        self.ax.set_zlabel('Z (m) - Up')
        self.ax.set_title('Hexapod Robot - Real-time Visualization')
        
        # Set reasonable limits based on robot size
        body = self.config.robot.body
        margin = max(body.length, body.width) * 0.8
        
        self.ax.set_xlim([-margin, margin])
        self.ax.set_ylim([-margin, margin])
        self.ax.set_zlim([-margin/2, margin])
        
        # Equal aspect ratio
        self.ax.set_box_aspect([1,1,0.5])
        
        # Grid and styling
        self.ax.grid(True, alpha=0.3)
        self.ax.view_init(elev=20, azim=45)
        
        # Add interactive controls info
        info_text = (
            "Controls:\n"
            "• Mouse: Rotate view\n" 
            "• Scroll: Zoom in/out\n"
            "• R: Reset view\n"
            "• T: Toggle body\n"
            "• L: Toggle legs\n"
            "• C: Toggle coordinates"
        )
        self.fig.text(0.02, 0.98, info_text, fontsize=9, verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # Set up key press events
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.fig.canvas.mpl_connect('scroll_event', self._mouse_scroll)
        
    def _draw_body(self):
        """Draw the robot body outline."""
        if not self.show_body:
            return
            
        # Clear previous body lines
        for line in self.body_lines:
            line.remove()
        self.body_lines.clear()
        
        # Body dimensions
        body = self.config.robot.body
        l, w, h = body.length/2, body.width/2, body.height/2
        
        # Define body corner points
        corners = [
            [-l, -w, -h], [l, -w, -h], [l, w, -h], [-l, w, -h],  # Bottom
            [-l, -w, h], [l, -w, h], [l, w, h], [-l, w, h]       # Top
        ]
        
        # Draw body edges
        edges = [
            # Bottom face
            [0, 1], [1, 2], [2, 3], [3, 0],
            # Top face  
            [4, 5], [5, 6], [6, 7], [7, 4],
            # Vertical edges
            [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        
        for edge in edges:
            p1, p2 = corners[edge[0]], corners[edge[1]]
            line = self.ax.plot3D(
                [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                color=self.body_color, linewidth=2, alpha=0.7
            )[0]
            self.body_lines.append(line)
    
    def _draw_coordinate_system(self):
        """Draw coordinate system axes."""
        if not self.show_coordinates:
            return
            
        # Clear previous coordinate lines
        for line in self.coord_lines:
            try:
                line.remove()
            except Exception:
                pass
        self.coord_lines.clear()
        
        # Axis length
        axis_len = max(self.config.robot.body.length, self.config.robot.body.width) * 0.3
        
        # X-axis (red)
        line = self.ax.plot3D([0, axis_len], [0, 0], [0, 0], color='red', linewidth=3, alpha=0.8)[0]
        self.coord_lines.append(line)
        
        # Y-axis (green)  
        line = self.ax.plot3D([0, 0], [0, axis_len], [0, 0], color='green', linewidth=3, alpha=0.8)[0]
        self.coord_lines.append(line)
        
        # Z-axis (blue)
        line = self.ax.plot3D([0, 0], [0, 0], [0, axis_len], color='blue', linewidth=3, alpha=0.8)[0]
        self.coord_lines.append(line)
    
    def _draw_legs(self):
        """Draw leg positions and connections."""
        if not self.show_legs:
            return
            
        # Clear previous leg elements
        for line in self.leg_lines:
            line.remove()
        for point in self.leg_points:
            point.remove()
        self.leg_lines.clear()
        self.leg_points.clear()
        # Clear joints
        for line in self.joint_lines:
            line.remove()
        for pt in self.joint_points:
            pt.remove()
        for txt in self.joint_texts:
            try:
                txt.remove()
            except Exception:
                pass
        self.joint_lines.clear()
        self.joint_points.clear()
        self.joint_texts.clear()
        joint_coord_texts = []
        target_coord_texts = []
        origin_coord_texts = []
        origin_arrow_artists = []
        
        # Draw each leg
        for i in range(6):
            leg_config = self.config.get_leg_config(i)
            
            # Leg attachment point (fixed)
            attach_pos = leg_config.position
            
            # Current leg target (if available)
            if i in self.state.leg_positions:
                target_pos = self.state.leg_positions[i]
                
                # Draw line from attachment point to current position
                line = self.ax.plot3D(
                    [attach_pos[0], target_pos[0]], 
                    [attach_pos[1], target_pos[1]], 
                    [attach_pos[2], target_pos[2]],
                    color=self.leg_color, linewidth=2, alpha=0.8
                )[0]
                self.leg_lines.append(line)
                
                # Draw target position point
                point = self.ax.scatter(
                    target_pos[0], target_pos[1], target_pos[2],
                    color=self.leg_color, s=50, alpha=0.9
                )
                self.leg_points.append(point)
            
            # Draw attachment point
            point = self.ax.scatter(
                attach_pos[0], attach_pos[1], attach_pos[2],
                color='black', s=30, alpha=0.8
            )
            self.leg_points.append(point)

            # Annotate leg origin (attachment) coordinates if enabled
            if getattr(self.config.visualization, 'show_leg_origin_coords', False):
                # Text label for origin coordinates
                try:
                    origin_coord_texts.append(
                        self.ax.text(
                            attach_pos[0], attach_pos[1], attach_pos[2] + 0.005,
                            f"{attach_pos[0]:.3f},{attach_pos[1]:.3f},{attach_pos[2]:.3f}",
                            fontsize=6, color='darkgreen'
                        )
                    )
                except Exception:
                    pass
                # Small local coordinate frame arrows (projected X/Y in horizontal plane, Z up)
                try:
                    # Define a small scale relative to body size
                    axis_scale = max(self.config.robot.body.length, self.config.robot.body.width) * 0.06
                    rot = leg_config.rotation
                    cosr, sinr = math.cos(rot), math.sin(rot)
                    # Local forward (leg +X) arrow (use red)
                    fx = attach_pos[0] + cosr * axis_scale
                    fy = attach_pos[1] + sinr * axis_scale
                    fz = attach_pos[2]
                    forward_line = self.ax.plot3D([attach_pos[0], fx], [attach_pos[1], fy], [attach_pos[2], fz], color='red', linewidth=1.2, alpha=0.85)[0]
                    # Side direction (local +Y) rotate forward by +90° in horizontal plane
                    sx = attach_pos[0] + (-sinr) * axis_scale
                    sy = attach_pos[1] + (cosr) * axis_scale
                    sz = attach_pos[2]
                    side_line = self.ax.plot3D([attach_pos[0], sx], [attach_pos[1], sy], [attach_pos[2], sz], color='green', linewidth=1.2, alpha=0.85)[0]
                    # Up direction (local +Z) always world up
                    ux = attach_pos[0]
                    uy = attach_pos[1]
                    uz = attach_pos[2] + axis_scale
                    up_line = self.ax.plot3D([attach_pos[0], ux], [attach_pos[1], uy], [attach_pos[2], uz], color='blue', linewidth=1.2, alpha=0.85)[0]
                    origin_arrow_artists.extend([forward_line, side_line, up_line])
                except Exception:
                    pass

            # Draw joint chain if enabled and link lengths available
            if getattr(self.config.visualization, 'show_joints', True):
                leg_cfg_model = self.config.robot.legs[i]
                link_lengths = getattr(leg_cfg_model, 'link_lengths', None)
                leg_angles = self.state.leg_angles.get(i)
                if link_lengths and leg_angles:
                    # Normalize link lengths: if 2 provided (legacy), treat as femur,tibia with zero-length coxa
                    if len(link_lengths) == 2:
                        coxa_len = 0.0
                        femur_len, tibia_len = link_lengths
                    else:
                        coxa_len, femur_len, tibia_len = link_lengths[:3]

                    # Apply calibrated offsets (assume offsets represent mechanical zero so effective = raw - offset)
                    coxa_angle = leg_angles[0] - leg_cfg_model.joint_angle_offsets[0]
                    femur_angle = leg_angles[1] - leg_cfg_model.joint_angle_offsets[1]
                    tibia_angle = leg_angles[2] - leg_cfg_model.joint_angle_offsets[2]

                    base_x, base_y, base_z = attach_pos
                    rot = leg_cfg_model.rotation
                    cosr, sinr = math.cos(rot), math.sin(rot)

                    # Coxa rotates about body Z axis (yaw) giving horizontal displacement only
                    # We rotate forward vector by coxa_angle within horizontal plane relative to nominal rotation.
                    nominal_forward = (cosr, sinr, 0.0)
                    # Effective horizontal direction after coxa yaw: rotate nominal forward by coxa_angle around Z
                    cosc, sinc = math.cos(coxa_angle), math.sin(coxa_angle)
                    dir_x = nominal_forward[0]*cosc - nominal_forward[1]*sinc
                    dir_y = nominal_forward[0]*sinc + nominal_forward[1]*cosc
                    dir_z = 0.0
                    # Coxa end point
                    coxa_end = (base_x + dir_x * coxa_len, base_y + dir_y * coxa_len, base_z)

                    # Femur pitch: we approximate vertical plane defined by dir vector and Z
                    femur_dx = femur_len * math.cos(femur_angle) * dir_x
                    femur_dy = femur_len * math.cos(femur_angle) * dir_y
                    femur_dz = femur_len * math.sin(femur_angle)
                    femur_end = (coxa_end[0] + femur_dx, coxa_end[1] + femur_dy, coxa_end[2] + femur_dz)

                    # Tibia relative from femur end with (femur + tibia) pitch
                    total_pitch = femur_angle + tibia_angle
                    tibia_dx = tibia_len * math.cos(total_pitch) * dir_x
                    tibia_dy = tibia_len * math.cos(total_pitch) * dir_y
                    tibia_dz = tibia_len * math.sin(total_pitch)
                    tibia_end = (femur_end[0] + tibia_dx, femur_end[1] + tibia_dy, femur_end[2] + tibia_dz)

                    # Draw segments
                    if coxa_len > 0.0:
                        seg_coxa = self.ax.plot3D(
                            [base_x, coxa_end[0]], [base_y, coxa_end[1]], [base_z, coxa_end[2]],
                            color=self.joint_color, linewidth=2, alpha=0.9
                        )[0]
                        self.joint_lines.append(seg_coxa)
                    seg_femur = self.ax.plot3D(
                        [coxa_end[0], femur_end[0]], [coxa_end[1], femur_end[1]], [coxa_end[2], femur_end[2]],
                        color=self.joint_color, linewidth=2, alpha=0.9
                    )[0]
                    seg_tibia = self.ax.plot3D(
                        [femur_end[0], tibia_end[0]], [femur_end[1], tibia_end[1]], [femur_end[2], tibia_end[2]],
                        color=self.joint_color, linewidth=2, alpha=0.9
                    )[0]
                    self.joint_lines.extend([seg_femur, seg_tibia])
                    # Joint points (exclude base attachment already drawn)
                    if coxa_len > 0.0:
                        jp_coxa = self.ax.scatter(coxa_end[0], coxa_end[1], coxa_end[2], color=self.joint_color, s=40, alpha=0.9)
                        self.joint_points.append(jp_coxa)
                    jp_femur = self.ax.scatter(femur_end[0], femur_end[1], femur_end[2], color=self.joint_color, s=40, alpha=0.9)
                    jp_tibia = self.ax.scatter(tibia_end[0], tibia_end[1], tibia_end[2], color=self.joint_color, s=40, alpha=0.9)
                    self.joint_points.extend([jp_femur, jp_tibia])

                    # Annotate angles
                    try:
                        y_off = 0.005
                        if getattr(self.config.visualization, 'show_joint_angles', True):
                            if coxa_len > 0.0:
                                txtc = self.ax.text(coxa_end[0], coxa_end[1], coxa_end[2]+y_off, f"C:{math.degrees(coxa_angle):.0f}°", fontsize=7, color='black')
                                self.joint_texts.append(txtc)
                            txtf = self.ax.text(femur_end[0], femur_end[1], femur_end[2]+y_off, f"F:{math.degrees(femur_angle):.0f}°", fontsize=7, color='black')
                            txtt = self.ax.text(tibia_end[0], tibia_end[1], tibia_end[2]+y_off, f"T:{math.degrees(tibia_angle):.0f}°", fontsize=7, color='black')
                            self.joint_texts.extend([txtf, txtt])
                        # Annotate coordinates if enabled
                        if getattr(self.config.visualization, 'show_joint_coords', False):
                            fmt = lambda p: f"({p[0]:.3f},{p[1]:.3f},{p[2]:.3f})"
                            if coxa_len > 0.0:
                                joint_coord_texts.append(self.ax.text(coxa_end[0], coxa_end[1], coxa_end[2]-y_off, fmt(coxa_end), fontsize=6, color='dimgray'))
                            joint_coord_texts.append(self.ax.text(femur_end[0], femur_end[1], femur_end[2]-y_off, fmt(femur_end), fontsize=6, color='dimgray'))
                            joint_coord_texts.append(self.ax.text(tibia_end[0], tibia_end[1], tibia_end[2]-y_off, fmt(tibia_end), fontsize=6, color='dimgray'))
                    except Exception:
                        pass

            # Target (foot) coordinate annotation
            if getattr(self.config.visualization, 'show_target_coords', False) and i in self.state.leg_positions:
                p = self.state.leg_positions[i]
                try:
                    target_coord_texts.append(self.ax.text(p[0], p[1], p[2]+0.01, f"{p[0]:.3f},{p[1]:.3f},{p[2]:.3f}", fontsize=6, color='navy'))
                except Exception:
                    pass

        # Extend tracking lists so they can be removed next frame
        self.joint_texts.extend(joint_coord_texts)
        self.joint_texts.extend(target_coord_texts)
        self.joint_texts.extend(origin_coord_texts)
        # Track arrow artists for cleanup (reuse leg_lines to auto-clean next frame)
        self.leg_lines.extend(origin_arrow_artists)
    
    def _update_plot(self, frame):
        """Update the 3D plot with current data."""
        # Process any new data from the queue
        data_processed = 0
        while not self.data_queue.empty():
            try:
                leg_data = self.data_queue.get_nowait()
                self.state.update_leg(leg_data)
                data_processed += 1
            except queue.Empty:
                break
        
        # Update performance stats
        self.frame_count += 1
        current_time = time.time()
        
        # Calculate FPS every second
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.fps_start_time)
            self.frame_count = 0
            self.fps_start_time = current_time
            
            # Calculate data rate
            data_count = sum(len(self.state.leg_positions) for _ in [1])  # Count active legs
            time_delta = current_time - self.last_data_time
            if time_delta > 0:
                self.data_rate = (data_count - self.last_data_count) / time_delta
            self.last_data_count = data_count
            self.last_data_time = current_time
        
        # Redraw all elements
        self._draw_body()
        self._draw_coordinate_system() 
        self._draw_legs()
        
        # Update title with comprehensive status
        active_legs = len(self.state.leg_positions)
        queue_size = self.data_queue.qsize()
        status_text = (
            f'Hexapod Robot | Active Legs: {active_legs}/6 | '
            f'FPS: {self.current_fps:.1f} | Queue: {queue_size} | '
            f'Time: {current_time:.1f}s'
        )
        self.ax.set_title(status_text)
        
        return self.body_lines + self.leg_lines + self.leg_points + self.coord_lines
    
    def _on_key_press(self, event):
        """Handle keyboard input for interactive controls."""
        if event.key == 'r':
            # Reset view
            self.ax.view_init(elev=20, azim=45)
            self.fig.canvas.draw()
            
        elif event.key == 't':
            # Toggle body display
            self.show_body = not self.show_body
            print(f"Body display: {'ON' if self.show_body else 'OFF'}")
            
        elif event.key == 'l':
            # Toggle legs display
            self.show_legs = not self.show_legs
            print(f"Legs display: {'ON' if self.show_legs else 'OFF'}")
            
        elif event.key == 'c':
            # Toggle coordinates display
            self.show_coordinates = not self.show_coordinates
            print(f"Coordinates display: {'ON' if self.show_coordinates else 'OFF'}")
            
        elif event.key == 'h':
            # Show help
            help_text = """
Hexapod Visualizer Controls:
• Mouse drag: Rotate view
• Mouse scroll: Zoom in/out
• R: Reset view to default
• T: Toggle body outline
• L: Toggle leg display
• C: Toggle coordinate axes
• H: Show this help
• ESC or Q: Quit (close window)
            """
            print(help_text)
            
        elif event.key in ['escape', 'q']:
            # Quit
            plt.close(self.fig)
            self.stop_visualization()
    
    def _mouse_scroll(self, event):
        """Handle mouse scroll for zooming."""
        if event.button == 'up':
            # Zoom in - get current limits and shrink them
            xl = self.ax.get_xlim()
            yl = self.ax.get_ylim() 
            zl = self.ax.get_zlim()
            
            # Shrink by 10%
            factor = 0.9
            cx, cy, cz = (xl[0]+xl[1])/2, (yl[0]+yl[1])/2, (zl[0]+zl[1])/2
            dx, dy, dz = (xl[1]-xl[0])*factor/2, (yl[1]-yl[0])*factor/2, (zl[1]-zl[0])*factor/2
            
            self.ax.set_xlim([cx-dx, cx+dx])
            self.ax.set_ylim([cy-dy, cy+dy])
            self.ax.set_zlim([cz-dz, cz+dz])
            
        elif event.button == 'down':
            # Zoom out - expand limits by 10%
            xl = self.ax.get_xlim()
            yl = self.ax.get_ylim()
            zl = self.ax.get_zlim()
            
            factor = 1.1
            cx, cy, cz = (xl[0]+xl[1])/2, (yl[0]+yl[1])/2, (zl[0]+zl[1])/2
            dx, dy, dz = (xl[1]-xl[0])*factor/2, (yl[1]-yl[0])*factor/2, (zl[1]-zl[0])*factor/2
            
            self.ax.set_xlim([cx-dx, cx+dx])
            self.ax.set_ylim([cy-dy, cy+dy])
            self.ax.set_zlim([cz-dz, cz+dz])
            
        self.fig.canvas.draw()
    
    def _serial_reader_thread(self):
        """Thread function for reading serial data."""
        reader = SerialReader(self.config)
        
        if not reader.connect():
            print("Failed to connect to serial port")
            return
            
        print("Serial reader thread started")
        
        try:
            while self.running:
                leg_data = reader.read_and_parse()
                if leg_data:
                    try:
                        self.data_queue.put_nowait(leg_data)
                    except queue.Full:
                        # Queue full, remove oldest item and add new one
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put_nowait(leg_data)
                        except queue.Empty:
                            pass
                            
        except Exception as e:
            print(f"Serial reader error: {e}")
        finally:
            reader.disconnect()
            print("Serial reader thread stopped")
    
    def start_visualization(self):
        """Start the real-time visualization."""
        print(f"Starting hexapod visualization at {self.update_rate} FPS")
        
        # Start serial reading thread
        self.running = True
        self.serial_thread = threading.Thread(target=self._serial_reader_thread, daemon=True)
        self.serial_thread.start()
        
        # Start animation
        self.animation = FuncAnimation(
            self.fig, self._update_plot, 
            interval=1000//self.update_rate,  # Convert FPS to milliseconds
            blit=False,  # Don't use blitting for 3D plots
            cache_frame_data=False
        )
        
        # Show the plot
        plt.tight_layout()
        plt.show()
        
        # Cleanup when window is closed
        self.running = False
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.join(timeout=2.0)
    
    def stop_visualization(self):
        """Stop the visualization and cleanup."""
        self.running = False
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        plt.close(self.fig)


def main():
    """Main entry point for the visualizer."""
    print("Hexapod 3D Visualizer")
    print("Loading configuration...")
    
    try:
        # Load configuration
        config = ConfigLoader.load_config("config.yaml")
        print(f"✓ Configuration loaded successfully!")
        
        # Create and start visualizer
        visualizer = HexapodVisualizer(config)
        
        print("Starting 3D visualization...")
        print("Close the plot window to exit.")
        
        visualizer.start_visualization()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())