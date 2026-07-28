
with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'r') as f:
    content = f.read()

target = """            snkHtml+='<div class="audio-node-meta">Type: '+esc(s.type)+' · State: '+esc(s.state||'IDLE')+'</div>';
            if(s.volume!==null){"""
replacement = """            let badgeClass = (s.state === 'DISCONNECTED' || s.state === 'MISSING') ? 'err' : 'ok';
            snkHtml+='<div class="audio-node-meta">Type: '+esc(s.type)+' · State: <span class="badge '+badgeClass+'">'+esc(s.state||'IDLE')+'</span></div>';
            if (s.state === 'DISCONNECTED' && s.type === 'bt') {
                snkHtml+='<div style="margin-top: 0.5rem;"><button onclick="taBtConnect(\\''+jsarg(s.mac||'')+'\\')" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: #1f6feb; border: none; border-radius: 4px; color: white;">🔌 Connect BT</button></div>';
            }
            if (s.state === 'DISCONNECTED' && s.type === 'dlna_output') {
                snkHtml+='<div style="margin-top: 0.5rem;"><button onclick="taDlnaScan()" style="font-size: 0.75rem; padding: 0.3rem 0.6rem; background: #238636; border: none; border-radius: 4px; color: white;">🔍 Scan DLNA</button></div>';
            }
            if(s.volume!==null && s.present !== false){"""

if target in content:
    with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'w') as f:
        f.write(content.replace(target, replacement))
    print("Patched app.js sink rendering")
else:
    print("Target not found")
