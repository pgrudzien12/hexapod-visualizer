#!/usr/bin/env python3
"""
Test script for hexapod parser with sample data.
"""

from main import HexapodParser

def test_parser():
    """Test the parser with sample log data."""
    parser = HexapodParser()
    
    # Sample log lines from the documentation
    test_lines = [
        "I (39868) wbc: (39599638)Leg 0 IK: BodyXYZ(0.106, 0.280, -0.043) -> LegXYZ(0.230, -0.026, -0.043) -> LegAng(-0.112, 0.025, 0.768)",
        "I (39878) wbc: (39609641)Leg 1 IK: BodyXYZ(0.050, 0.300, -0.035) -> LegXYZ(0.200, -0.020, -0.035) -> LegAng(-0.100, 0.030, 0.750)",
        "I (39888) wbc: (39619644)Leg 2 IK: BodyXYZ(-0.050, 0.280, -0.040) -> LegXYZ(0.180, -0.015, -0.040) -> LegAng(-0.085, 0.020, 0.720)",
        "Invalid line format",  # Test error handling
        "",  # Test empty line
    ]
    
    print("Testing hexapod parser with sample data:")
    print("=" * 120)
    
    for i, line in enumerate(test_lines):
        print(f"Test {i+1}: {line[:80]}{'...' if len(line) > 80 else ''}")
        
        leg_data = parser.parse_line(line)
        if leg_data:
            output = parser.format_output(leg_data)
            print(f"  ✓ Parsed: {output}")
        else:
            print(f"  ✗ Failed to parse or empty line")
        print()
    
    print("Parser test completed!")

if __name__ == "__main__":
    test_parser()