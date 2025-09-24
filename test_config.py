#!/usr/bin/env python3
"""
Test script for configuration loading and validation.
"""

from config_loader import ConfigLoader
import math

def test_configuration(config_file: str):
    """Test loading a specific configuration file."""
    print(f"\n=== Testing {config_file} ===")
    try:
        config = ConfigLoader.load_config(config_file)
        print(f"✓ Configuration loaded successfully!")
        
        # Test serial settings
        print(f"Serial: {config.serial.port} @ {config.serial.baudrate} baud, timeout={config.serial.timeout}s")
        
        # Test robot configuration
        body = config.robot.body
        print(f"Body: {body.length}×{body.width}×{body.height} m")
        
        # Test all legs
        print("Legs:")
        for i in range(6):
            leg = config.get_leg_config(i)
            deg = math.degrees(leg.rotation)
            print(f"  {i}: {leg.name:<12} pos=({leg.position[0]:6.3f}, {leg.position[1]:6.3f}, {leg.position[2]:6.3f}) rot={leg.rotation:6.3f}rad ({deg:6.1f}°)")
        
        # Test visualization settings
        viz = config.visualization
        print(f"Visualization: {viz.update_rate}fps, buffer={viz.buffer_size}, body={viz.show_body}, legs={viz.show_legs}")
        
        # Test data settings
        data = config.data
        print(f"Data: {data.coordinate_system}, {data.units}, smoothing={data.enable_smoothing}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading {config_file}: {e}")
        return False

def main():
    """Test all configuration files."""
    configs_to_test = [
        "config.yaml",
        "config_example_alt.yaml", 
        "config_compact.yaml"
    ]
    
    success_count = 0
    for config_file in configs_to_test:
        if test_configuration(config_file):
            success_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Successfully loaded {success_count}/{len(configs_to_test)} configurations")
    
    # Test creating a default config
    print("\n=== Creating Default Config ===")
    try:
        ConfigLoader.create_default_config("config_generated.yaml")
        print("✓ Default configuration created")
        
        # Test loading the generated config
        test_configuration("config_generated.yaml")
        
    except Exception as e:
        print(f"✗ Error creating default config: {e}")

if __name__ == "__main__":
    main()