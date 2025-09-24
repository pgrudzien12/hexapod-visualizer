#!/usr/bin/env python3
"""
Hexapod Visualizer - Serial Data Reader and Parser
Connects to serial port and parses incoming hexapod inverse kinematics data.
Uses configuration file for flexible setup.
"""

import serial
import re
import sys
import math
from typing import Optional, Dict, Any
from dataclasses import dataclass

from config_loader import ConfigLoader, HexapodConfig, LegConfiguration


@dataclass
class LegData:
    """Data structure for parsed leg kinematics information."""
    leg_number: int
    timestamp: int
    body_xyz: tuple[float, float, float]
    leg_xyz: tuple[float, float, float]
    leg_angles: tuple[float, float, float]
    leg_config: Optional[LegConfiguration] = None  # Associated leg configuration


class HexapodParser:
    """Parser for hexapod inverse kinematics log data."""
    
    def __init__(self, config: HexapodConfig):
        self.config = config
        # Regex pattern to parse the log format
        # Example: I (39868) wbc: (39599638)Leg 0 IK: BodyXYZ(0.106, 0.280, -0.043) -> LegXYZ(0.230, -0.026, -0.043) -> LegAng(-0.112, 0.025, 0.768)
        self.pattern = re.compile(
            r'I \(\d+\) wbc: \((\d+)\)Leg (\d+) IK: '
            r'BodyXYZ\(([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+)\) -> '
            r'LegXYZ\(([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+)\) -> '
            r'LegAng\(([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+), ([-+]?\d*\.?\d+)\)'
        )
    
    def parse_line(self, line: str) -> Optional[LegData]:
        """
        Parse a single log line and extract kinematics data.
        
        Args:
            line: Raw log line from serial port
            
        Returns:
            LegData object if parsing successful, None otherwise
        """
        line = line.strip()
        if not line:
            return None
            
        match = self.pattern.match(line)
        if not match:
            return None
            
        try:
            groups = match.groups()
            timestamp = int(groups[0])
            leg_number = int(groups[1])
            
            # Parse BodyXYZ coordinates
            body_xyz = (float(groups[2]), float(groups[3]), float(groups[4]))
            
            # Parse LegXYZ coordinates  
            leg_xyz = (float(groups[5]), float(groups[6]), float(groups[7]))
            
            # Parse LegAng servo angles (in radians)
            leg_angles = (float(groups[8]), float(groups[9]), float(groups[10]))
            
            # Get leg configuration if available
            leg_config = None
            try:
                leg_config = self.config.get_leg_config(leg_number)
            except ValueError:
                pass  # Leg not found in configuration, continue without config
            
            return LegData(
                leg_number=leg_number,
                timestamp=timestamp,
                body_xyz=body_xyz,
                leg_xyz=leg_xyz,
                leg_angles=leg_angles,
                leg_config=leg_config
            )
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing line: {line} - {e}")
            return None
    
    def format_output(self, leg_data: LegData) -> str:
        """Format parsed leg data for display."""
        leg_name = f"({leg_data.leg_config.name})" if leg_data.leg_config else ""
        
        base_output = (
            f"Leg {leg_data.leg_number:1d} {leg_name:<13} | "
            f"Time: {leg_data.timestamp:8d}μs | "
            f"Body: ({leg_data.body_xyz[0]:6.3f}, {leg_data.body_xyz[1]:6.3f}, {leg_data.body_xyz[2]:6.3f}) | "
            f"Leg: ({leg_data.leg_xyz[0]:6.3f}, {leg_data.leg_xyz[1]:6.3f}, {leg_data.leg_xyz[2]:6.3f}) | "
            f"Angles: ({leg_data.leg_angles[0]:6.3f}, {leg_data.leg_angles[1]:6.3f}, {leg_data.leg_angles[2]:6.3f})"
        )
        
        # Add configuration info if available
        if leg_data.leg_config:
            config_info = (
                f" | Cfg: pos=({leg_data.leg_config.position[0]:5.3f}, {leg_data.leg_config.position[1]:5.3f}, {leg_data.leg_config.position[2]:5.3f}) "
                f"rot={leg_data.leg_config.rotation:5.3f}rad ({math.degrees(leg_data.leg_config.rotation):4.1f}°)"
            )
            return base_output + config_info
        
        return base_output


class SerialReader:
    """Handle serial communication with the hexapod robot."""
    
    def __init__(self, config: HexapodConfig):
        self.config = config
        self.port = config.serial.port
        self.baudrate = config.serial.baudrate
        self.timeout = config.serial.timeout
        self.serial_conn = None
        self.parser = HexapodParser(config)
    
    def connect(self) -> bool:
        """
        Establish serial connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
            
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Serial connection closed")
    
    def read_and_parse(self) -> Optional[LegData]:
        """
        Read one line from serial port and parse it.
        
        Returns:
            LegData object if successful, None otherwise
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
            
        try:
            # Read line from serial port
            line = self.serial_conn.readline().decode('utf-8', errors='ignore')
            
            # Parse the line
            return self.parser.parse_line(line)
            
        except serial.SerialException as e:
            print(f"Serial read error: {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"Unicode decode error: {e}")
            return None
    
    def run_continuous(self):
        """Run continuous data reading and parsing loop."""
        print("Starting continuous data reading... (Press Ctrl+C to stop)")
        print("=" * 160)
        
        try:
            while True:
                leg_data = self.read_and_parse()
                if leg_data:
                    output = self.parser.format_output(leg_data)
                    print(output)
                    
        except KeyboardInterrupt:
            print("\nStopping data reading...")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            self.disconnect()


def main():
    """Main entry point."""
    print("Hexapod Visualizer - Serial Data Reader")
    print("Loading configuration...")
    
    try:
        # Load configuration
        config = ConfigLoader.load_config("config.yaml")
        print(f"✓ Configuration loaded successfully!")
        print(f"Serial: {config.serial.port} at {config.serial.baudrate} baud")
        print(f"Robot: {len(config.robot.legs)} legs configured")
        
        # Display leg configuration
        print("\nLeg Configuration:")
        for i in range(6):
            leg = config.get_leg_config(i)
            print(f"  Leg {i}: {leg.name:<12} pos=({leg.position[0]:6.3f}, {leg.position[1]:6.3f}, {leg.position[2]:6.3f}) rot={leg.rotation:6.3f}rad ({math.degrees(leg.rotation):5.1f}°)")
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return 1
    
    # Create serial reader instance with configuration
    reader = SerialReader(config)
    
    # Attempt connection
    if not reader.connect():
        print("Failed to establish serial connection. Exiting.")
        return 1
    
    # Run continuous reading
    reader.run_continuous()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
