# Hexapod Visualizer

Real-time 3D visualization system for hexapod robot inverse kinematics data. Connects to serial port to receive live data and displays the robot in 3D with configurable visualization options.

## Features

### 🔧 Configuration System
- **Flexible serial settings**: Configurable COM port and baud rate
- **Robot geometry**: Define leg positions and rotations in body coordinates
- **Visualization options**: Customizable colors, update rates, and display elements
- **Multiple configurations**: Supports different hexapod layouts and designs

### 📊 Real-time Data Processing
- **Serial communication**: Connects to robot via configurable COM port
- **Data parsing**: Extracts inverse kinematics data from log format
- **Performance monitoring**: FPS tracking and data rate statistics
- **Buffering**: Smooth animation despite irregular data timing

### 🎮 3D Visualization
- **Interactive 3D display**: Real-time matplotlib-based visualization
- **Multiple view modes**: Toggle body, legs, and coordinate axes
- **Mouse controls**: Rotate view by dragging, zoom with scroll wheel
- **Keyboard shortcuts**: Quick access to display options and view reset
 - **Joint chain rendering**: Visualizes coxa, femur, tibia segments with angle annotations

### 🎯 Demo Mode
- **Simulated patterns**: Test visualization without robot connection
- **Tripod gait**: Realistic walking pattern simulation
- **Wave motion**: Smooth wave-like movement demonstration

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd hexapod_visualizer
   ```

2. **Set up Python environment**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate (Windows)
   .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure your robot**:
   - Edit `config.yaml` to match your hexapod layout
   - Set correct COM port and baud rate
   - Adjust leg positions and rotations

## Usage

### Live Visualization (with robot)
```bash
# Connect to robot and visualize real-time data
python main.py        # Text-based parser only
python visualizer.py  # 3D visualization
```

### Demo Mode (without robot)
```bash
# Test with simulated movement patterns
python demo.py
```

## Configuration

### Serial Settings
```yaml
serial:
  port: "COM5"          # Serial port
  baudrate: 115200      # Baud rate
  timeout: 1.0          # Read timeout
```

### Robot Geometry
```yaml
robot:
  body:
    length: 0.200       # Body dimensions (meters)
    width: 0.150
    height: 0.050
  
  legs:
    0:  # Leg 0 configuration
      name: "Left Front"
      position: [0.075, 0.075, 0.0]    # Attachment point [x,y,z]
      rotation: 0.7854                 # Rotation from X-axis (radians)
      link_lengths: [0.068, 0.088, 0.127]  # [coxa, femur, tibia] lengths (m)
      joint_angle_offsets: [0.0, 0.5396943301595464, 1.0160719600939494] # Calibration offsets (radians)
```

### Visualization Options
```yaml
visualization:
  update_rate: 60       # Target FPS
  buffer_size: 100      # Data buffer size
  show_body: true       # Display body outline
  show_legs: true       # Display leg positions
  show_coordinates: true # Display coordinate axes
  show_joints: true     # Draw articulated joint chain
  show_joint_angles: true # Annotate joint angles (C/F/T)
  show_joint_coords: false  # Annotate each joint endpoint (x,y,z)
  show_target_coords: false # Annotate foot/target point (x,y,z)
  show_leg_origin_coords: false # Annotate each leg attachment origin (x,y,z)
  colors:               # RGB colors (0-255)
    body: [100, 100, 100]
    legs: [50, 150, 200]
    coordinates: [255, 0, 0]
    joints: [255, 215, 0]
```

## Controls

### Keyboard Controls
- **R**: Reset view to default angle
- **T**: Toggle body outline display
- **L**: Toggle leg display
- **C**: Toggle coordinate axes display
- **H**: Show help information
- **ESC/Q**: Quit application

### Mouse Controls
- **Drag**: Rotate 3D view
- **Scroll**: Zoom in/out
- **Right-click**: Context menu (matplotlib default)

## Data Format

The system parses inverse kinematics log data in the following format:
```
I (39868) wbc: (39599638)Leg 0 IK: BodyXYZ(0.106, 0.280, -0.043) -> LegXYZ(0.230, -0.026, -0.043) -> LegAng(-0.112, 0.025, 0.768)
```

Where:
- `39599638`: Robot timestamp (microseconds)
- `Leg 0`: Leg index (0-5)
- `BodyXYZ`: 3D position in body coordinates (meters)
- `LegXYZ`: 3D position in leg coordinates (meters)
- `LegAng`: Servo angles (radians)

### Joint Angles & Calibration
Each leg reports raw servo angles: `(coxa, femur, tibia)` in radians. These are adjusted by `joint_angle_offsets` from the configuration to account for mechanical zero calibration:
```
effective_angle = raw_angle - offset  # Offsets represent mechanical zero bias
```
The visualized chain uses these effective angles. If only two `link_lengths` are provided, the system assumes a zero-length coxa for backward compatibility.

## Coordinate Systems

### Body Coordinates (Right-Hand System)
- **X-axis**: Forward direction
- **Y-axis**: Left side (positive)
- **Z-axis**: Upward (positive)

### Leg Layout
```
    0(L-Front)     3(R-Front)
    1(L-Mid)       4(R-Mid)  
    2(L-Back)      5(R-Back)
```

## Files Structure

```
hexapod_visualizer/
├── main.py              # Serial reader and parser
├── visualizer.py        # 3D visualization system
├── demo.py             # Demo mode with simulated patterns
├── config_loader.py    # Configuration management
├── config.yaml         # Main configuration file
├── config_example_*.yaml # Example configurations
├── test_*.py          # Test scripts
├── pyproject.toml     # Project dependencies
└── README.md          # This file
```

## Dependencies

- **Python 3.12+**: Modern Python with type hints
- **matplotlib**: 3D plotting and visualization
- **numpy**: Mathematical operations and arrays
- **pyserial**: Serial port communication
- **pydantic**: Configuration validation
- **PyYAML**: YAML configuration file parsing

## Performance

- **Real-time capable**: Handles ~100Hz data updates
- **Configurable frame rate**: 1-120 FPS visualization
- **Efficient rendering**: Optimized for smooth animation
- **Memory management**: Bounded data buffers

## Troubleshooting

### Serial Connection Issues
- Verify COM port in Device Manager (Windows)
- Check baud rate matches robot settings
- Ensure no other programs are using the port
- Try different timeout values

### Visualization Performance
- Lower `update_rate` in configuration
- Reduce `buffer_size` for less memory usage
- Disable elements (body/legs/coordinates) if not needed
- Close other heavy applications

### Configuration Errors
- Validate YAML syntax
- Check all 6 legs are defined (0-5)
- Verify numeric values are valid
- Use test scripts to validate configuration

## Development

### Adding New Features
1. Follow existing code patterns
2. Add configuration options to schema
3. Update validation in `config_loader.py`
4. Test with both live and demo data

### Testing
```bash
python test_config.py    # Test configuration loading
python test_parser.py    # Test data parsing
python demo.py           # Test visualization
```
