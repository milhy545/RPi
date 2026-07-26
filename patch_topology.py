import sys

with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'r') as f:
    content = f.read()

target = """    let sources=(r&&r.sources)||[], sinks=(r&&r.sinks)||[], defSink=(r&&r.default_sink)||'';"""
replacement = """    let sources=(r&&r.sources)||[], sinks=(r&&r.sinks)||[], defSink=(r&&r.default_sink)||'';
    let d = (r && r.devices) || {};
    // Add disconnected/known sinks for topology UI
    let knownSinks = [];
    if(d.hdmi) knownSinks.push({id: 'hdmi', name: d.hdmi.name || 'HDMI', type: 'hdmi', state: d.hdmi.present ? 'ACTIVE' : 'MISSING', volume: d.hdmi.volume, present: d.hdmi.present});
    if(d.bt_soundbar) knownSinks.push({id: 'bt', name: d.bt_soundbar.name || 'BT Soundbar', type: 'bt', state: d.bt_soundbar.present ? 'ACTIVE' : 'DISCONNECTED', volume: d.bt_soundbar.volume, present: d.bt_soundbar.present, mac: d.bt_soundbar.mac, paired: d.bt_soundbar.paired});
    if(d.dlna_output) knownSinks.push({id: 'dlna', name: d.dlna_output.name || 'DLNA Output', type: 'dlna_output', state: r.dlna_connected ? 'CONNECTED' : 'DISCONNECTED', volume: d.dlna_output.volume, present: d.dlna_output.present});
    
    // Merge knownSinks into sinks, avoiding duplicates by type
    knownSinks.forEach(ks => {
        if(!sinks.some(s => s.type === ks.type || (s.name && s.name.includes(ks.name)))) {
            sinks.push(ks);
        }
    });"""

if target in content:
    with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'w') as f:
        f.write(content.replace(target, replacement))
    print("Patched app.js to include disconnected sinks")
else:
    print("Target not found")
