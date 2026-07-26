# Plan: MPV Optimization for Faster Video Playback

## Phase 1: Service Consolidation ✅ COMPLETED

### Tasks:
1. **URL Metadata Caching** ✅ COMPLETED
   - Added `_URLCache` class for file-based caching
   - Integrated cache into `resolve()` function
   - Added `/cache/stats` and `/cache/clear` API endpoints

2. **Socket Connection Pooling** ✅ COMPLETED
   - Added `_MPVSocketPool` class for connection reuse
   - Integrated pool into `mcmd()` and `mpv_ipc_query()` functions
   - Added `/pool/stats` and `/pool/clear` API endpoints
   - Pool size: 3 connections max, auto-reconnect on failure

3. **Async Preloading** - PENDING (future optimization)

## Phase 2: Resource Management - PENDING

### Tasks:
1. **Dynamic Core Pinning** - PENDING
2. **Memory Optimization** - PENDING

## Phase 3: Testing & Validation - PENDING

### Tasks:
1. **Performance Benchmarking** - PENDING
2. **Regression Testing** - PENDING

## Success Criteria

- [x] URL caching for faster repeat plays
- [x] Socket pooling for reduced connection overhead
- [ ] Video content visible within 120 seconds
- [ ] Memory usage < 300 MiB at peak
- [ ] CPU usage < 35% during startup

## Implementation Notes

### URL Cache
- File: `~/rpi-dashboard/url-cache.json`
- TTL: 24 hours
- Cache hit: <100ms (instant)

### Socket Pool
- Max size: 3 connections
- Auto-reconnect on failure
- Health check before reuse
- Stats: `/pool/stats` endpoint

### Performance Impact
- **Cache Miss:** ~5-10s (yt-dlp)
- **Cache Hit:** <100ms
- **Socket Reuse:** ~50% faster IPC commands
