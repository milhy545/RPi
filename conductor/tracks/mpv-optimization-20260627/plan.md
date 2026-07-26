# Plan: MPV Optimization for Faster Video Playback

## 1. Specification Summary

### 1.1 Problem
The RPi Dashboard video playback experience suffers from prolonged load times. Users experience 5+ minute delays from clicking "Play" to actual video content, causing significant user friction in a TV-first interface.

### 1.2 Current State
- **Time to Playback:** ~5 minutes (300+ seconds)
- **Peak Memory:** ~500 MiB
- **CPU Usage:** ~70% during startup
- **Architecture:** Dual MPV implementations (webserver.py + services/player.py)
- **Redundancy:** 3+ systemd services for core functionality

### 1.3 Target Performance
- **Time to Playback:** < 120 seconds (60% improvement)
- **Memory Usage:** < 300 MiB (40% reduction)
- **CPU Usage:** < 35% during startup
- **Success Criteria:** Video visible within 120 seconds of "Play"

### 1.4 Requirements
- ✅ Video content visible within 120 seconds of playback initiation
- ✅ Memory usage < 300 MiB at peak playback
- ✅ CPU usage < 35% during startup phase
- ✅ No regression in existing functionality (CEC, audio routing, WebUI)
- ✅ TUI mode switching remains < 500ms

## 2. Implementation Strategy

### 2.1 Phase 1: Service Consolidation (Days 1-2)
**Objective:** Eliminate redundant services and modernize MPV implementation

#### Tasks:
1. **Remove webserver.py MPV implementation**
   - Replace with modern service-based approach
   - Preserve non-MPV WebUI functionality
   - Update systemd service definitions

2. **Consolidate MPV services**
   - Update `rpi_dashboard/services/player.py`
   - Implement unified service architecture
   - Remove deprecated `keys2mpv.service`
   - Maintain TUI and WebUI functionality

3. **Implement startup optimization**
   - Add early socket connection establishment
   - Implement asynchronous preload mechanisms
   - Optimize concurrency for non-blocking startup

#### Deliverables:
- Consolidated `webserver.py` (API-only)
- Enhanced `rpi_dashboard/services/player.py`
- Updated systemd service definitions
- Conductor integration

### 2.2 Phase 2: Resource Management (Days 3-4)
**Objective:** Optimize memory and CPU usage

#### Tasks:
1. **Dynamic core pinning**
   - Implement content-aware core allocation
   - Use 1-2 cores for standard content (720p, <1 hour)
   - Use 1-3 cores for high-demand content (1080p+, >1 hour)

2. **Memory pressure management**
   - Add real-time memory monitoring
   - Implement allocation throttling
   - Add garbage collection optimization

3. **MPV startup optimization**
   - Replace slow DRM modes with GPU acceleration
   - Implement early video format detection
   - Optimize command-line arguments based on content

#### Deliverables:
- Core allocation logic
- Memory monitoring system
- Optimized MPV startup pipeline
- Performance metrics collector

### 2.3 Phase 3: Caching and Preloading (Days 5-6)
**Objective:** Reduce redundant operations

#### Tasks:
1. **Video metadata caching**
   - Cache YouTube metadata after first resolution
   - Implement content-based caching strategies
   - Add cache invalidation mechanisms

2. **Socket connection pooling**
   - Reuse established IPC connections
   - Implement connection reuse logic
   - Add connection health monitoring

3. **Asynchronous loading**
   - Implement non-blocking metadata fetching
   - Add background preload capabilities
   - Optimize I/O operations

#### Deliverables:
- Metadata caching system
- Connection pooling implementation
- Async pipeline
- Preload mechanisms

### 2.4 Phase 4: Testing and Validation (Day 7)
**Objective:** Verify performance improvements

#### Tasks:
1. **Performance benchmarking**
   - Measure before/after metrics
   - Validate all targets met
   - Identify remaining bottlenecks

2. **Regression testing**
   - Test existing functionality
   - Validate CEC controls
   - Test audio routing
   - Test TUI mode switching

3. **Load testing**
   - Test concurrent access
   - Validate memory usage under load
   - Test system stability

#### Deliverables:
- Performance test suite
- Regression test suite
- Load test results
- Validation report

## 3. Risk Management

### 3.1 High-Risk Areas
1. **Service Consolidation**
   - **Risk:** Breaking existing functionality
   - **Mitigation:** Comprehensive testing, feature parity validation
   - **Contingency:** Maintain backup implementations during rollout

2. **Performance Targets**
   - **Risk:** Insufficient improvement
   - **Mitigation:** A/B testing, gradual rollout
   - **Contingency:** Rollback strategies ready

3. **Memory Optimization**
   - **Risk:** System instability under load
   - **Mitigation:** Gradual optimization, monitoring
   - **Contingency:** Resource caps implemented

### 3.2 Medium-Risk Areas
1. **Code Refactoring**
   - **Risk:** Introducing bugs
   - **Mitigation:** Comprehensive test coverage, peer review
   - **Contingency:** Feature flags for gradual rollout

2. **User Experience Changes**
   - **Risk:** Changing familiar behavior
   - **Mitigation:** User acceptance testing
   - **Contingency:** UX validation with user feedback

### 3.3 Low-Risk Areas
1. **Documentation Updates**
   - **Risk:** Outdated information
   - **Mitigation:** Automated documentation generation
   - **Contingency:** Manual review process

## 4. Testing Strategy

### 4.1 Automated Tests
```bash
# Performance tests
python3 tests/test_performance.py

# Regression tests
pytest tests/test_mpv_optimization.py -v

# Memory tests
python3 tests/test_memory_usage.py

# Integration tests
python3 tests/test_webserver_integration.py
```

### 4.2 Manual Testing
- Video playback testing with various content types
- UI responsiveness verification
- CEC integration testing
- Audio routing validation
- Concurrent access testing

### 4.3 Performance Monitoring
```bash
# Real-time metrics collection
python3 tools/performance_monitor.py --output metrics.json

# Alerting on degradation
python3 tools/alert_on_regression.py
```

## 5. Deployment Plan

### 5.1 Rollout Strategy
1. **Stage 1:** Service consolidation
2. **Stage 2:** Resource optimization
3. **Stage 3:** Caching and preloading
4. **Stage 4:** Production deployment

### 5.2 Rollback Strategy
- **Immediate:** Restore previous working state
- **Functional:** Feature flags for gradual rollout
- **Performance:** Monitor and rollback if targets not met

### 5.3 Monitoring
- Real-time performance dashboards
- Automated performance regression alerts
- Resource usage monitoring
- User experience tracking

## 6. Team Preparation

### 6.1 Training
- Performance optimization techniques
- New testing frameworks
- Monitoring and alerting setup

### 6.2 Documentation
- Updated API documentation
- Performance tuning guides
- Troubleshooting documentation

## 7. Success Metrics

### 7.1 Performance Metrics
- **Time to Playback:** < 120 seconds
- **Memory Usage:** < 300 MiB
- **CPU Usage:** < 35%
- **Success Rate:** > 95%

### 7.2 Quality Metrics
- **Test Coverage:** > 90%
- **Regression Rate:** < 5%
- **User Satisfaction:** > 90%

## 8. Dependencies

### 8.1 Technical Dependencies
- yt-dlp (Python library)
- MPV (media player)
- Systemd (init system)
- Python 3.12

### 8.2 Environmental Dependencies
- RPi 3 Model B+ for testing
- Milhy-PC for development
- Tailscale for connectivity

## 9. Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1 | 2 days | Service consolidation |
| Phase 2 | 2 days | Resource optimization |
| Phase 3 | 2 days | Caching and preloading |
| Phase 4 | 1 day | Testing and validation |
| **Total** | **7 days** | **Complete optimization** |

## 10. Completion Criteria

### 10.1 Technical Criteria
- [ ] Service consolidation completed
- [ ] Performance targets met
- [ ] All regression tests passed
- [ ] Documentation updated
- [ ] Monitoring setup complete

### 10.2 User Experience Criteria
- [ ] UI remains responsive
- [ ] Video loads quickly
- [ ] Audio routing works
- [ ] CEC controls functional
- [ ] Mode switching performs as expected

## 11. Communication Plan

### 11.1 Internal Communication
- Daily standup reports
- Weekly demos
- Sprint reviews

### 11.2 Stakeholder Communication
- Performance reports
- Status updates
- Risk mitigation updates

## 12. Cost-Benefit Analysis

### 12.1 Benefits
- **User Experience:** 60% faster video loading
- **Resource Usage:** 40% less memory, 50% less CPU
- **System Stability:** Reduced crashes, better resource management
- **User Satisfaction:** Improved overall dashboard experience

### 12.2 Costs
- **Development Time:** 7 days
- **Resource Impact:** Temporary increased CPU during development
- **Testing Overhead:** Comprehensive test suite required

### 12.3 ROI
- **High Impact:** Significant user experience improvement
- **Quick Payback:** Performance improvements visible within days
- **Sustainable:** Long-term resource savings

## 13. Continuous Improvement

### 13.1 Monitoring Setup
- Real-time performance dashboards
- Automated alerting on degradation
- Resource usage tracking

### 13.2 Enhancement Backlog
- Adaptive quality-of-service
- Smart caching strategies
- Predictive resource allocation

---

**Plan Status:** Ready for Implementation
**Next Step:** Begin Phase 1 with service consolidation

*Plan created: 2026-07-27*
*Version: 1.0*
*Review Cycle: 7 days*