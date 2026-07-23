-- RPi-TV runs as a lingering user and normally has no active logind session.
-- This must load after 50-bluez-config.lua and before 90-enable-all.lua.
bluez_monitor.properties["with-logind"] = false
