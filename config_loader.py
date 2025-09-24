#!/usr/bin/env python3
"""
Configuration loader for hexapod visualizer.
Handles loading and validation of YAML configuration files.
"""

import os
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import yaml
from pydantic import BaseModel, Field, field_validator


@dataclass
class LegConfiguration:
    """Configuration for a single leg."""
    name: str
    position: Tuple[float, float, float]  # [x, y, z] in body coordinates
    rotation: float  # Rotation from body X-axis in radians


class SerialConfig(BaseModel):
    """Serial communication configuration."""
    port: str = "COM5"
    baudrate: int = 115200
    timeout: float = 1.0
    
    @field_validator('baudrate')
    @classmethod
    def validate_baudrate(cls, v):
        valid_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if v not in valid_rates:
            raise ValueError(f'Baudrate must be one of: {valid_rates}')
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v


class BodyConfig(BaseModel):
    """Robot body configuration."""
    length: float = Field(gt=0, description="Body length in meters")
    width: float = Field(gt=0, description="Body width in meters")  
    height: float = Field(gt=0, description="Body height in meters")


class LegConfig(BaseModel):
    """Individual leg configuration."""
    name: str
    position: List[float] = Field(min_items=3, max_items=3)
    rotation: float
    
    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        if len(v) != 3:
            raise ValueError('Position must have exactly 3 coordinates [x, y, z]')
        return v
    
    @field_validator('rotation')
    @classmethod
    def validate_rotation(cls, v):
        # Normalize rotation to [-2π, 2π] range
        if abs(v) > 2 * math.pi:
            import warnings
            warnings.warn(f'Large rotation angle {v:.3f} rad ({math.degrees(v):.1f}°). Consider normalizing.')
        return v


class RobotConfig(BaseModel):
    """Robot physical configuration."""
    body: BodyConfig
    legs: Dict[int, LegConfig]
    
    @field_validator('legs')
    @classmethod
    def validate_legs(cls, v):
        # Check that we have exactly 6 legs numbered 0-5
        expected_legs = set(range(6))
        actual_legs = set(v.keys())
        
        if actual_legs != expected_legs:
            missing = expected_legs - actual_legs
            extra = actual_legs - expected_legs
            error_msg = []
            if missing:
                error_msg.append(f"Missing legs: {sorted(missing)}")
            if extra:
                error_msg.append(f"Extra legs: {sorted(extra)}")
            raise ValueError(f"Must have exactly 6 legs (0-5). {', '.join(error_msg)}")
        
        return v


class VisualizationConfig(BaseModel):
    """Visualization settings."""
    update_rate: int = Field(ge=1, le=120, default=60)
    buffer_size: int = Field(ge=10, le=1000, default=100)
    show_body: bool = True
    show_legs: bool = True
    show_coordinates: bool = True
    colors: Dict[str, List[int]] = {
        "body": [100, 100, 100],
        "legs": [50, 150, 200], 
        "coordinates": [255, 0, 0]
    }
    
    @field_validator('colors')
    @classmethod
    def validate_colors(cls, v):
        for color_name, rgb in v.items():
            if len(rgb) != 3:
                raise ValueError(f'Color {color_name} must have 3 RGB values')
            if not all(0 <= val <= 255 for val in rgb):
                raise ValueError(f'Color {color_name} RGB values must be 0-255')
        return v


class DataConfig(BaseModel):
    """Data processing configuration."""
    coordinate_system: str = Field(default="right_hand", pattern="^(right_hand|left_hand)$")
    units: str = Field(default="meters", pattern="^(meters|millimeters)$")
    enable_smoothing: bool = False
    smoothing_window: int = Field(ge=1, le=50, default=5)


class HexapodConfig(BaseModel):
    """Complete hexapod configuration."""
    serial: SerialConfig = SerialConfig()
    robot: RobotConfig
    visualization: VisualizationConfig = VisualizationConfig()
    data: DataConfig = DataConfig()
    
    def get_leg_config(self, leg_id: int) -> LegConfiguration:
        """Get configuration for a specific leg."""
        if leg_id not in self.robot.legs:
            raise ValueError(f"Leg {leg_id} not found in configuration")
        
        leg = self.robot.legs[leg_id]
        return LegConfiguration(
            name=leg.name,
            position=tuple(leg.position),
            rotation=leg.rotation
        )
    
    def get_all_legs(self) -> List[LegConfiguration]:
        """Get configuration for all legs in order."""
        return [self.get_leg_config(i) for i in range(6)]


class ConfigLoader:
    """Configuration file loader with validation."""
    
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> HexapodConfig:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file. If None, looks for config.yaml in current directory.
            
        Returns:
            Validated HexapodConfig object
            
        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If configuration is invalid
        """
        if config_path is None:
            config_path = Path("config.yaml")
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {e}")
        
        try:
            config = HexapodConfig(**config_data)
            return config
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    @staticmethod
    def create_default_config(output_path: str = "config_default.yaml"):
        """Create a default configuration file."""
        default_config = {
            'serial': {
                'port': 'COM5',
                'baudrate': 115200,
                'timeout': 1.0
            },
            'robot': {
                'body': {
                    'length': 0.200,
                    'width': 0.150,
                    'height': 0.050
                },
                'legs': {
                    0: {'name': 'Left Front', 'position': [0.075, 0.075, 0.0], 'rotation': 0.7854},
                    1: {'name': 'Left Middle', 'position': [0.0, 0.085, 0.0], 'rotation': 1.5708},
                    2: {'name': 'Left Back', 'position': [-0.075, 0.075, 0.0], 'rotation': 2.3562},
                    3: {'name': 'Right Front', 'position': [0.075, -0.075, 0.0], 'rotation': -0.7854},
                    4: {'name': 'Right Middle', 'position': [0.0, -0.085, 0.0], 'rotation': -1.5708},
                    5: {'name': 'Right Back', 'position': [-0.075, -0.075, 0.0], 'rotation': -2.3562}
                }
            },
            'visualization': {
                'update_rate': 60,
                'buffer_size': 100,
                'show_body': True,
                'show_legs': True,
                'show_coordinates': True,
                'colors': {
                    'body': [100, 100, 100],
                    'legs': [50, 150, 200],
                    'coordinates': [255, 0, 0]
                }
            },
            'data': {
                'coordinate_system': 'right_hand',
                'units': 'meters',
                'enable_smoothing': False,
                'smoothing_window': 5
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        print(f"Default configuration created at: {output_path}")


def main():
    """Test the configuration loader."""
    try:
        # Test loading existing config
        config = ConfigLoader.load_config("config.yaml")
        print("✓ Configuration loaded successfully!")
        print(f"Serial port: {config.serial.port}")
        print(f"Baudrate: {config.serial.baudrate}")
        print(f"Number of legs: {len(config.robot.legs)}")
        
        # Test leg access
        for i in range(6):
            leg = config.get_leg_config(i)
            print(f"Leg {i}: {leg.name} at {leg.position}, rotation {leg.rotation:.3f} rad ({math.degrees(leg.rotation):.1f}°)")
            
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print("Creating default configuration...")
        ConfigLoader.create_default_config()


if __name__ == "__main__":
    main()