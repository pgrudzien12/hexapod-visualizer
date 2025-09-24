# Hexapod Visualizer - AI Coding Agent Instructions

## Project Overview
This is a Python 3.12+ project for **real-time visualization** of live hexapod robot data via serial communication. The system connects to COM5 by default and renders 3D visualizations of inverse kinematics calculations received every ~10ms from the robot.

## Development Environment
- **Python Version**: 3.12 (managed with `.python-version`)
- **Dependency Management**: Uses `pyproject.toml` with modern Python packaging standards
- **Virtual Environment**: `.venv/` directory (excluded from git)

## Architecture & Domain Knowledge

### Serial Communication Protocol
The robot streams inverse kinematics data via COM5 (default) at ~10ms intervals:
```
I (39868) wbc: (39599638)Leg 0 IK: BodyXYZ(0.106, 0.280, -0.043) -> LegXYZ(0.230, -0.026, -0.043) -> LegAng(-0.112, 0.025, 0.768)
```

**Log Format Breakdown:**
- `39599638`: Robot timestamp in microseconds (can be ignored for visualization)
- `Leg 0 IK`: Leg index (0-5) with inverse kinematics data
- `BodyXYZ(x,y,z)`: 3D point in robot body coordinate system
- `LegXYZ(x,y,z)`: Same point transformed to leg coordinate system
- `LegAng(servo1, servo2, servo3)`: Calculated servo angles in radians
- all distances in meters

### Coordinate Systems & Robot Layout
**Body Coordinates (Right-Hand System):**
- X-axis: Forward direction
- Y-axis: Left side
- Z-axis: Upward

**Leg Coordinates (Right-Hand System, per leg):**
- X-axis: Outward from body center
- Y-axis: Following right-hand rule
- Z-axis: Forward direction

**Leg Layout:**
```
    0(L-Front)     3(R-Front)
    1(L-Mid)       4(R-Mid)  
    2(L-Back)      5(R-Back)
```
- Legs 0-2: Left side (forward, mid, back)
- Legs 3-5: Right side (forward, mid, back)

## Development Patterns

### Real-Time Data Processing
Handle continuous data streams from COM5:
- **Non-blocking serial reads** to maintain visualization frame rate
- **Data buffering** for smooth animation despite irregular timing
- **Parser resilience** for malformed or incomplete log lines
- **Coordinate system transformations** between body and leg frames

### Visualization Architecture
Structure for real-time 3D rendering:
- **Separate threads** for serial reading and rendering
- **State synchronization** between data collection and visualization
- **Frame rate management** independent of data arrival frequency
- **Interactive camera controls** while maintaining real-time updates

### Visualization Libraries
Common Python libraries for this domain:
- **matplotlib** with 3D plotting for basic visualizations
- **pygame** or **pyglet** for real-time interactive displays
- **Open3D** or **VTK** for advanced 3D rendering
- **numpy** for mathematical operations and transformations
- **pyserial** for COM5 communication

### Mathematical Conventions
- Use **numpy arrays** for vector operations and transformations
- Angles typically in **radians** internally, degrees for user interfaces
- **Right-hand coordinate system** is standard in robotics
- Transform matrices as 4x4 homogeneous coordinates

## Key Development Workflows

### Adding New Features
1. Start with mathematical model validation in simple scripts
2. Create unit tests for kinematics calculations
3. Build visualization components incrementally
4. Test with various robot configurations

### Testing Strategy
- Unit tests for kinematic calculations (accuracy critical)
- Integration tests for gait generation
- Visual validation through rendered output comparison
- Performance tests for real-time animation requirements

## Common Implementation Patterns

## Dependencies to Consider
When adding features, commonly needed packages include:
- `numpy` for mathematical operations
- `scipy` for optimization (inverse kinematics)
- `matplotlib` or visualization libraries
- `pydantic` for configuration validation
- `pytest` for testing framework

## Code Quality Standards
- Use type hints for all function parameters and returns
- Follow PEP 8 style guidelines for Python code
- Use 'uv' for dependency management and packaging; they should always be added using terminal commands
- Remeber to start virtual environment with `source .venv/bin/activate` before running scripts
