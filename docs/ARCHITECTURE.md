# RPi-TV Dashboard Architecture

## Overview

RPi-TV Dashboard is a web-based control interface for Raspberry Pi media center. It provides:
- **WebUI** — Responsive web interface for desktop, tablet, and mobile
- **TUI** — Terminal-based dashboard for direct RPi access
- **API** — RESTful API for programmatic access

## Project Structure

```
rpi-dashboard/
├── rpi_dashboard/              # Main package
│   ├── api/                    # API layer
│   │   ├── handlers.py         # Request handlers
│   │   └── routes.py           # Route registry
│   ├── services/               # Business logic
│   │   ├── audio.py            # Audio routing, mixer, DLNA
│   │   ├── cec.py              # HDMI-CEC control
│   │   ├── devices.py          # Bluetooth, WiFi, devices
│   │   ├── player.py           # mpv player control
│   │   ├── system.py           # System stats, restart
│   │   └── terminal.py         # WebSocket terminal
│   ├── models/                 # Data models
│   │   └── schemas.py          # API response schemas
│   ├── tui/                    # Terminal UI
│   │   └── modern.py           # Modern Textual dashboard
│   └── static/                 # WebUI assets
│       ├── index.html          # Main HTML template
│       ├── css/
│       │   ├── main.css        # Core styles
│       │   ├── themes.css      # Theme variables
│       │   └── responsive.css  # Media queries
│       └── js/
│           └── app.js          # Frontend logic
├── tests/                      # Test suite
│   ├── test_services_*.py      # Service unit tests
│   ├── test_tui_modern.py      # TUI tests
│   └── e2e/                    # E2E tests
├── webserver.py                # HTTP server (legacy)
├── tui.py                      # Original TUI (legacy)
└── conductor/                  # Project management
    └── tracks/                 # Development tracks
```

## Architecture Layers

### 1. Presentation Layer

#### WebUI (static/)
- **HTML**: Semantic markup with data-i18n attributes
- **CSS**: CSS Grid/Flexbox with CSS custom properties
- **JavaScript**: Vanilla JS with async/await API calls
- **Features**:
  - Responsive design (desktop/tablet/mobile)
  - Dark/Light theme system
  - i18n support (CZ/EN)
  - PWA manifest

#### TUI (tui/modern.py)
- **Framework**: Textual (Python TUI framework)
- **Features**:
  - Real-time system stats
  - Device management
  - Settings controls
  - Keyboard shortcuts

### 2. API Layer (api/)

#### Routes (routes.py)
```python
ROUTES = {
    "/audio/state": handle_audio_state,
    "/mpv/play": handle_mpv_play,
    "/devices/state": handle_devices_state,
    # ...
}
```

#### Handlers (handlers.py)
- Parse request parameters
- Call service functions
- Return JSON responses

### 3. Service Layer (services/)

#### Audio Service (audio.py)
- PipeWire/PulseAudio integration
- Audio routing and mixing
- DLNA renderer support
- Bluetooth audio

#### Player Service (player.py)
- mpv IPC communication
- Playback control
- Resume memory
- EOF detection

#### Devices Service (devices.py)
- Bluetooth pairing/management
- WiFi configuration
- Device discovery

#### CEC Service (cec.py)
- HDMI-CEC commands
- TV control (power, volume, navigation)

#### System Service (system.py)
- CPU/RAM/Temperature monitoring
- Service management
- Network information

### 4. Data Layer

#### Models (models/schemas.py)
```python
@dataclass
class AudioState:
    default_sink: Optional[str]
    sinks: List[AudioDevice]
    sources: List[AudioDevice]
    # ...
```

## Data Flow

```
User Action → WebUI/TUI → API Handler → Service → System Tool → Response
     ↓                                                      ↓
  Browser ← JSON Response ← Handler ← Service ← Command Output
```

## Key Design Decisions

### 1. Service Layer Pattern
- **Why**: Separates business logic from HTTP/TUI concerns
- **Benefit**: Testable, reusable, maintainable

### 2. Static File Serving
- **Why**: Faster than inline HTML/JS
- **Benefit**: Better caching, cleaner code

### 3. CSS Custom Properties
- **Why**: Theme system without JavaScript
- **Benefit**: Instant theme switching, system preference detection

### 4. Async Services
- **Why**: Non-blocking system calls
- **Benefit**: Responsive UI during long operations

## Testing Strategy

### Unit Tests
- Service functions with mocked system calls
- Handler functions with mocked services
- Model validation

### Integration Tests
- API endpoint testing
- Service integration

### E2E Tests
- Playwright browser tests
- Full user workflow testing

## Performance Considerations

### RPi 3B+ Constraints
- **RAM**: 1GB limit
- **CPU**: 4x 1.4GHz
- **Storage**: SD card I/O

### Optimizations
- Lazy loading of static assets
- Audio state caching (0.75s TTL)
- Minimal DOM updates
- Efficient PipeWire/PulseAudio queries

## Security

### Input Validation
- All API parameters validated
- SQL injection prevention (N/A - no database)
- XSS prevention (escape output)

### Rate Limiting
- 1 second between requests per IP
- Action endpoints rate-limited

### Network Security
- IP allowlist (LAN + Tailscale)
- HTTPS support
- CORS headers

## Future Improvements

### Short Term
- [ ] Complete TUI Devices tab
- [ ] Add unit tests for all handlers
- [ ] Improve error messages

### Medium Term
- [ ] WebSocket for real-time updates
- [ ] Service worker for offline support
- [ ] More theme options

### Long Term
- [ ] Plugin system
- [ ] Multi-language support
- [ ] Mobile app (React Native)
