# Spec: MPV Optimization for Faster Video Playback

## 1. Problem Statement

Users experience excessive wait times between clicking "Play" on video content and actual video playback in the RPi Dumb TV Dashboard. Current mean time to video playback exceeds 5 minutes, causing significant friction in a TV-first interface where immediate responsiveness is critical.

## 2. Current State Analysis

### 2.1 Performance Metrics
- **Time to Playback:** ~5 minutes (300+ seconds)
- **Peak Memory Usage:** ~500 MiB
- **CPU Utilization:** ~70% during startup
- **Video Content Resolution:** Variable, often HD/4K
- **Startup Components:** Multiple redundant services, DRM initialization, yt-dlp resolution

### 2.2 Technical Architecture
- **Dual MPV Implementations:** Webserver.py (legacy) + rpi_dashboard/services/player.py (modern)
- **Redundant Services:** 3+ systemd services for core functionality
- **Blocking Operations:** Sequential initialization of multiple background processes
- **Synchronous Loading:** Single-threaded startup blocking UI responsiveness

### 2.3 User Experience Impact
- **TV Interface Lag:** Noticeable delay when switching from menu interaction
- **Remote Control Unresponsiveness:** User presses buttons, no immediate response
- **Multisession Issues:** When multiple users expect instant playback

## 3. Target Outcomes

### 3.1 Primary Performance Goals
- **Reduce Time to Playback:** From 300+ seconds to < 120 seconds (<60% improvement)
- **Optimize Memory Usage:** From ~500 MiB to < 300 MiB (<40% reduction)
- **Minimize CPU Impact:** From ~70% to < 35% during startup phase
- **Maintain Responsiveness:** UI interactions < 500ms

### 3.2 Secondary Benefits
- **Battery Efficiency:** Reduced power consumption during startup
- **System Stability:** Fewer crashes during high-load operations
- **Scalability:** Better performance under concurrent load
- **User Satisfaction:** Improved overall dashboard experience

## 4. Constraints and Requirements

### 4.1 Technical Constraints
- **Memory Limit:** Total system RAM remains ~731 MiB
- **Compatibility:** Must maintain all existing features (CEC, audio routing, WebUI)
- **Architecture:** Backward-compatible changes required
- **Performance:** No regression in other functionality

### 4.2 Requirements
- **Functional Requirements:**
  - Video content visible within 120 seconds of "Play" button click
  - All existing functionality preserved (audio routing, CEC controls, mode switching)
  - System stability maintained under all conditions

- **Non-Functional Requirements:**
  - Response time < 500ms for UI interactions
  - Memory usage < 300 MiB during peak playback
  - CPU usage < 35% during startup
  - System must handle concurrent access gracefully

## 5. Success Criteria

### 5.1 Performance Validation
- **TC 001:** Video content appears within 120 seconds of playback initiation
- **TC 002:** System memory usage < 300 MiB at peak playback
- **TC 003:** CPU utilization < 35% during startup phase
- **TC 004:** TUI mode switching completes in < 500ms

### 5.2 Functional Validation
- **TC 005:** CEC controls continue to work correctly
- **TC 006:** Audio routing remains functional
- **TC 007:** WebUI controls accessible and responsive
- **TC 008:** Mode switching between dashboard and fullscreen apps

### 5.3 System Validation
- **TC 009:** No crashes during 24-hour continuous operation
- **TC 010:** Recovery from errors maintained
- **TC 011:** Graceful degradation under resource constraints

## 6. Technical Approach

### 6.1 Current Architecture Issues
1. **Service Redundancy:** Multiple services providing same or overlapping functionality
2. **Synchronous Initialization:** Blocking operations preventing parallel startup
3. **Inefficient Resource Management:** Excessive memory allocation and CPU usage
4. **Poor Caching Strategy:** Lack of effective caching for repeated operations

### 6.2 Optimization Strategy
1. **Service Consolidation:** Eliminate redundant implementations
2. **Asynchronous Loading:** Implement parallel startup for non-dependent components
3. **Dynamic Resource Allocation:** Adjust resource usage based on content requirements
4. **Smart Caching:** Implement intelligent caching strategies for repeated operations

### 6.3 Implementation Options
**Option A: Incremental Optimization**
- Maintain existing architecture
- Apply targeted performance improvements
- Longer implementation timeline

**Option B: Modernization Approach**
- Consolidate redundant services
- Implement modern async patterns
- Achieve aggressive performance targets

**Recommended:** **Option B** for significant performance gains

## 7. Risk Assessment

### 7.1 High-Risk Items
- **Service Consolidation:** Risk of breaking existing functionality
- **Memory Optimization:** Risk of crashes under heavy load
- **Performance Targets:** Risk of insufficient scope

### 7.2 Medium-Risk Items
- **Code Refactoring:** Risk of introducing bugs
- **Testing Coverage:** Risk of missing edge cases
- **User Experience:** Risk of changing familiar behavior

### 7.3 Low-Risk Items
- **Documentation Updates:** Low impact, high value
- **Code Cleanup:** Removes technical debt
- **Performance Monitoring:** Ongoing improvement

### 7.4 Risk Mitigation
- **Comprehensive Testing:** Unit, integration, and system tests
- **Feature Flags:** Gradual rollout capabilities
- **Rollback Strategies:** Ready for emergency situations
- **Performance Monitoring:** Real-time tracking and alerting

## 8. Testing Strategy

### 8.1 Automated Testing
- **Performance Tests:** Benchmark video loading times
- **Regression Tests:** Ensure existing functionality works
- **Memory Tests:** Validate memory usage constraints
- **Integration Tests:** Test end-to-end user journeys
- **Load Tests:** Simulate concurrent user access

### 8.2 Manual Testing
- **Video Playback Testing:** Various content types and resolutions
- **UI Responsiveness Testing:** User interaction tests
- **Cross-Device Testing:** Different input methods
- **Real-world Scenario Testing:** Typical user workflows

### 8.3 Validation Environment
- **Development:** Full feature set for initial testing
- **Staging:** Performance-optimized for validation
- **Production:** Gradual rollout with monitoring

## 9. Deployment Plan

### 9.1 Rollout Strategy
1. **Phase 1:** Service consolidation and cleanup
2. **Phase 2:** Performance optimizations and resource management
3. **Phase 3:** Advanced features and monitoring setup
4. **Phase 4:** Production deployment with gradual rollout

### 9.2 Rollback Plan
- **Immediate Rollback:** Restore previous working state
- **Performance Rollback:** Revert performance changes if targets not met
- **Functional Rollback:** Ensure all original functionality preserved

## 10. Team Preparation

### 10.1 Training
- **Team Training:** Performance optimization techniques
- **Documentation Updates:** New processes and procedures
- **Tool Training:** New monitoring and testing tools

### 10.2 Knowledge Transfer
- **Documentation:** Updated performance guides
- **Code Reviews:** Performance-focused code reviews
- **Best Practices:** Document lessons learned

## 11. Success Metrics

### 11.1 Quantitative Metrics
- **Performance:** Time to playback, memory usage, CPU utilization
- **Reliability:** Uptime, error rates, recovery times
- **User Experience:** Response times, satisfaction scores

### 11.2 Qualitative Metrics
- **User Feedback:** UI improvements, performance perception
- **Developer Experience:** Code maintainability, testability
- **Operational Excellence:** Monitoring effectiveness, incident response

## 12. Timeline and Resources

### 12.1 Estimated Timeline
- **Discovery:** 2 days
- **Implementation:** 5 days
- **Testing:** 3 days
- **Deployment:** 2 days
- **Total:** 12 days

### 12.2 Required Resources
- **Development Environment:** RPi 3 Model B+ for testing
- **Testing Infrastructure:** Automated test suite
- **Monitoring Tools:** Performance monitoring dashboards
- **Documentation:** Technical and user documentation

## 13. Dependencies

### 13.1 Internal Dependencies
- TUI codebase
- WebUI framework
- Audio routing system
- Existing MPV implementations

### 13.2 External Dependencies
- yt-dlp (Python library)
- MPV media player
- Systemd (init system)
- Python 3.12

## 14. Communication Plan

### 14.1 Internal Updates
- **Daily Standups:** Progress and blockers
- **Weekly Demos:** Functional demonstrations
- **Sprint Reviews:** Performance validation

### 14.2 Stakeholder Updates
- **Performance Reports:** Regular performance metrics
- **Status Updates:** Timeline and progress
- **Risk Reports:** Emerging risks and mitigations

## 15. Acceptance Criteria Checklist

### 15.1 Technical Checklist
- [ ] Service consolidation completed
- [ ] Performance targets met
- [ ] All existing functionality preserved
- [ ] Testing completed and passed
- [ ] Documentation updated

### 15.2 User Experience Checklist
- [ ] UI remains responsive
- [ ] Video loads quickly
- [ ] Audio routing works
- [ ] CEC controls functional
- [ ] Mode switching fast

## 16. Post-Implementation

### 16.1 Monitoring Setup
- **Performance Dashboards:** Real-time metrics
- **Alerting:** Performance degradation detection
- **Logging:** Comprehensive logging for analysis

### 16.2 Continuous Improvement
- **Performance Reviews:** Weekly optimization reviews
- **User Feedback:** Continuous user experience improvement
- **Technical Debt:** Regular refactoring sessions

### 16.3 Next Phase Considerations
- **Feature Expansion:** Enhanced user controls
- **Platform Expansion:** Additional input methods
- **Integration:** New media sources support

---

**Spec Status:** Ready for Implementation
**Next Action:** Obtain approval and begin Phase 1 implementation

*Spec created: 2026-07-27*
*Spec version: 1.0*
*Review cycle: Completed*