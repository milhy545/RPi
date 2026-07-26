import sys

with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'r') as f:
    content = f.read()

target = ".replace('alsa_output.platform-3f00b840.mailbox.stereo-fallback','Aux (3.5mm Jack)')"
replacement = ".replace('alsa_output.platform-3f00b840.mailbox.stereo-fallback','HDMI / Jack')"

if target in content:
    with open('/home/milhy777/rpi-dashboard/rpi_dashboard/static/js/app.js', 'w') as f:
        f.write(content.replace(target, replacement))
    print("Patched shortName")
else:
    print("Target not found")
