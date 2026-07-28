
with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/index.html', 'r') as f:
    content = f.read()

target = """    </div>

    <!-- Bluetooth Panel -->"""

replacement = """        <!-- Modern Audio Controls Below Topology -->
        <div class="audio-controls" style="display:flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
            <div style="display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; background: #161b22; border: 1px solid #30363d; padding: 1rem; border-radius: 8px;">
                <div>
                    <div style="font-weight: 500; margin-bottom: 0.2rem;" data-i18n="dlnaLatency">DLNA Latency Compensation</div>
                    <div style="font-size: 0.72rem; color: #8b949e;">Applies mpv audio-delay in milliseconds for DLNA sync. Positive delays audio.</div>
                </div>
                <div style="display:flex; gap:.4rem; align-items:center;">
                    <label style="font-size:.72rem;color:#8b949e">Delay (ms):</label>
                    <input type="number" id="ta-lat-dlna-offset" value="0" min="-5000" max="5000" step="50" style="width:80px; padding: 0.3rem; border: 1px solid #30363d; border-radius: 4px; background: #0d1117; color: var(--app-text)">
                    <button class="app-tab-btn" onclick="taSetLatency('dlna_output_offset_ms',$('#ta-lat-dlna-offset').value)" data-icon="💾" style="padding: 0.4rem 0.8rem; border-radius: 6px; background: #238636; color: #fff; border: 1px solid rgba(240,246,252,0.1);">Apply</button>
                </div>
            </div>
            
            <div style="display: flex; gap: 1rem; align-items: center; background: #161b22; border: 1px solid #30363d; padding: 1rem; border-radius: 8px;">
                <div style="flex: 1;">
                    <div style="font-weight: 500; margin-bottom: 0.2rem;">Expert Operations</div>
                    <div style="font-size: 0.72rem; color: #8b949e;">Restart services or reset audio patchbay to defaults.</div>
                </div>
                <button class="app-tab-btn" onclick="taRoute('reset')" style="padding: 0.4rem 0.8rem; border-radius: 6px;">Reset Matrix</button>
                <button class="app-tab-btn" onclick="restartMpv()" style="padding: 0.4rem 0.8rem; border-radius: 6px;">Restart MPV</button>
            </div>
        </div>
    </div>

    <!-- Bluetooth Panel -->"""

if target in content:
    with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/index.html', 'w') as f:
        f.write(content.replace(target, replacement))
    print("Patched index.html")
else:
    print("Target not found in index.html")
