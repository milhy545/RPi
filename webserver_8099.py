#!/usr/bin/env python3
"""RPi-TV v4.2 — fixed title, no black screen, fast CEC."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlsplit, urlunsplit
import html, json, os, re, socket, sys, subprocess, time, stat
import asyncio, threading
try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

# yt-dlp is installed in venv, no need for Kodi addon path

HOST, PORT = "0.0.0.0", 8099
KODI_H, KODI_P = "127.0.0.1", 9090
MSOCK = "/tmp/gfn-mpv.sock"
YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?.*?[?&]?v=|embed/|shorts/))([A-Za-z0-9_-]{11})")

QUALITY = {
    "360p": "best[height<=360][ext=mp4]/best[height<=360]",
    "480p": "best[height<=480][ext=mp4]/best[height<=480]",
    "720p": "best[height<=720][ext=mp4]/best[height<=720]",
    "1080p":"best[height<=1080][ext=mp4]/best[height<=1080]",
}
DQ = "360p"

def norm(u):
    u=u.strip()
    try: p=urlsplit(u)
    except: return u
    if p.scheme in ("http","https"): return urlunsplit((p.scheme,p.netloc,re.sub(r"/{2,}","/",p.path),p.query,p.fragment))
    return u

def yt_id(u):
    m=YT_RE.search(norm(u)); return m.group(1) if m else ""

def resolve(url, q=None):
    vid=yt_id(url)
    if not vid: return norm(url), {"title": url[:50]}
    fmt=QUALITY.get(q or DQ, QUALITY[DQ])
    try: import yt_dlp as youtube_dl
    except Exception as e: return url, {"error":str(e)}
    _co=os.path.join(os.path.dirname(os.path.abspath(__file__)),"yt-cookies.txt")
    _opts={"quiet":True,"no_warnings":True,"noplaylist":True,"format":fmt}
    if os.path.exists(_co): _opts["cookiefile"]=_co
    else: print(f"[WARN] Cookie file not found: {_co}", file=sys.stderr)
    with youtube_dl.YoutubeDL(_opts) as y:
        info=y.extract_info(f"https://youtu.be/{vid}", download=False)
    surl=info.get("url")
    if not surl:
        fmts=[f for f in (info.get("formats") or []) if f.get("url") and f.get("vcodec")!="none" and f.get("acodec")!="none"]
        fmts.sort(key=lambda f:(f.get("height") or 0), reverse=True)
        if fmts: surl=fmts[0].get("url")
    if not surl: raise RuntimeError("No playable URL")
    return surl, {"id":vid,"title":info.get("title",f"YT {vid}"),"h":info.get("height"),"dur":info.get("duration")}

def kodi_rpc(m, p=None, t=3):
    r={"jsonrpc":"2.0","method":m,"id":1}
    if p: r["params"]=p
    try:
        with socket.create_connection((KODI_H,KODI_P),timeout=t) as s:
            s.sendall(json.dumps(r).encode()+b"\n"); s.settimeout(t)
            d=b""
            while len(d)<65536:
                c=s.recv(4096)
                if not c: break
                d+=c
                if b"\n" in d: break
            dec=json.JSONDecoder(); probe=d.decode("utf-8","replace").lstrip()
            while probe:
                try: obj,i=dec.raw_decode(probe)
                except: break
                if isinstance(obj,dict) and obj.get("id")==1: return obj
                probe=probe[i:].lstrip()
    except: pass
    return {"result":[]}

# ── MPV ────────────────────────────────────────────────────────────────

_mpv=None; _mq=DQ; _mtitle=""

def mcmd(*a):
    if not os.path.exists(MSOCK): return {"error":"not running"}
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(MSOCK); s.settimeout(2)
        s.sendall((json.dumps({"command":list(a)})+"\n").encode())
        d=b""
        while True:
            c=s.recv(4096)
            if not c: break
            d+=c
            if b"\n" in d: break
        s.close(); return json.loads(d.decode().strip().split("\n")[-1])
    except Exception as e: return {"error":str(e)}

def mget(p): return mcmd("get_property",p)

def mpv_start(url, q=None):
    global _mpv,_mq,_mtitle
    mpv_stop(); _mq=q or _mq
    surl,meta=resolve(url,_mq)
    _mtitle=meta.get("title","Playing")
    cmd=["mpv",
         "--vo=drm","--drm-mode=640x480","--hwdec=v4l2m2m",
         "--fullscreen","--no-terminal","--ytdl=no","--ao=alsa",
         f"--title={_mtitle}",
         f"--input-ipc-server={MSOCK}","--keep-open=always",surl]
    _mpv=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {"ok":True,"pid":_mpv.pid,"url":surl,"meta":meta,"q":_mq}

def mpv_stop():
    global _mpv
    if _mpv and _mpv.poll() is None:
        _mpv.terminate()
        try: _mpv.wait(timeout=3)
        except: _mpv.kill()
    _mpv=None
    try: os.unlink(MSOCK)
    except: pass

def mpv_st():
    if not _mpv or _mpv.poll() is not None: return {"on":False}
    try:
        return {"on":True,"pid":_mpv.pid,
            "paused":mget("pause").get("data",False),
            "pos":mget("time-pos").get("data",0),
            "dur":mget("duration").get("data",0),
            "title":_mtitle or mget("media-title").get("data",""),
            "vol":mget("volume").get("data",100),"q":_mq}
    except: return {"on":True,"err":True,"title":_mtitle}

# ── CEC ────────────────────────────────────────────────────────────────

def cec_cmd(cmd, t=3):
    """CEC command - configure adapter each time for reliability."""
    def cec_result(tool, completed, ok_cmd):
        out = (completed.stdout + completed.stderr).strip()
        failed_markers = ("Tx, Timeout", "Max Retries", "Nacked", "Not Acknowledged", "attempting to send message without --to")
        if completed.returncode != 0 or any(marker in out for marker in failed_markers):
            return {"ok":False,"err":out[-500:] or f"{tool} exited {completed.returncode}"}
        return {"ok":True,"out":out[-500:] or ok_cmd}

    def run_cec(args, ok_cmd):
        r = subprocess.run(args, capture_output=True, text=True, timeout=t)
        return cec_result("cec-ctl", r, ok_cmd)

    def power_state():
        r = subprocess.run(
            ["cec-ctl","-d","/dev/cec0","--playback","--to","0","--give-device-power-status"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        out = (r.stdout + r.stderr).lower()
        if "pwr-state: on" in out:
            return "on"
        if "pwr-state: standby" in out:
            return "standby"
        if "pwr-state: to-on" in out:
            return "to-on"
        if "pwr-state: to-standby" in out:
            return "to-standby"
        return "unknown"

    try:
        # Map commands to cec-ctl args
        if cmd == "on 0":
            attempts = []
            for i in range(4):
                state_before = power_state()
                if state_before == "on":
                    active = run_cec(["cec-ctl","-d","/dev/cec0","--playback","--active-source","phys-addr=1.0.0.0"], "active-source")
                    return {"ok":True,"out":f"already on; active-source={active.get('ok')}"}

                result = run_cec(["cec-ctl","-d","/dev/cec0","--playback","--to","0","--image-view-on"], cmd)
                attempts.append({"attempt":i + 1,"before":state_before,"ok":result.get("ok"),"err":result.get("err","")[-120:]})
                time.sleep(8 if i == 0 else 10)
                state_after = power_state()
                attempts[-1]["after"] = state_after
                if state_after == "on":
                    active = run_cec(["cec-ctl","-d","/dev/cec0","--playback","--active-source","phys-addr=1.0.0.0"], "active-source")
                    return {"ok":True,"out":json.dumps(attempts),"active_source":active.get("ok")}
            return {"ok":False,"err":json.dumps(attempts)}
        elif cmd == "standby 0":
            args = ["cec-ctl","-d","/dev/cec0","--playback","--to","0","--standby"]
        elif cmd in ("volup","voldown","mute"):
            key = {"volup":"volume-up","voldown":"volume-down","mute":"mute"}[cmd]
            args = ["cec-ctl","-d","/dev/cec0","--playback","--to","0","--user-control-pressed",f"ui-cmd={key}","--user-control-released"]
        elif "user-control pressed" in cmd:
            import re as re2
            m = re2.search(r"'([^']+)'", cmd)
            if m:
                key = m.group(1)
                km = {"up":"up","down":"down","left":"left","right":"right","select":"select","back":"back","menu":"device-root-menu","channels+":"channel-up","channels-":"channel-down"}
                ui = km.get(key, key)
                args = ["cec-ctl","-d","/dev/cec0","--playback","--to","0","--user-control-pressed",f"ui-cmd={ui}","--user-control-released"]
            else:
                return {"ok":False,"err":"bad key"}
        elif cmd.startswith("active-source"):
            addr = cmd.split(" ", 1)[1] if " " in cmd else "phys-addr=1.0.0.0"
            args = ["cec-ctl","-d","/dev/cec0","--playback","--active-source",addr]
        else:
            # Fallback to cec-client for on/off
            r = subprocess.run(["cec-client","-s","-d","1","-p","0"], input=cmd, capture_output=True, text=True, timeout=t)
            return cec_result("cec-client", r, cmd)
        return run_cec(args, cmd)
    except subprocess.TimeoutExpired:
        return {"ok":False,"err":"timeout"}
    except Exception as e:
        return {"ok":False,"err":str(e)[:100]}
def cec_scan():
    """Scan CEC bus using cec-ctl."""
    try:
        r = subprocess.run(["cec-ctl","-d","/dev/cec0","-S"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()[:500] if r.stdout.strip() else "No devices"
    except: return "Timeout"
_bridg = None
def br_start():
    global _bridg
    br_stop()
    sc=r'''
import subprocess,json,os,socket,select,time,sys
MP="/tmp/gfn-mpv.sock"
def mc(c):
    if not os.path.exists(MP): return
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(MP);s.settimeout(1)
        s.sendall((json.dumps({"command":["parse-command",c]})+"\n").encode());s.recv(4096);s.close()
    except: pass
M={"play":"cycle pause","pause":"cycle pause","stop":"stop","backward":"seek -10",
   "forward":"seek 10","rewind":"seek -60","fast_forward":"seek 60",
   "left":"seek -10","right":"seek 10","select":"cycle pause","exit":"stop",
   "menu":"cycle pause","volume_up":"add volume 5","volume_down":"add volume -5","mute":"cycle mute"}
while True:
    p=subprocess.Popen(["cec-client","-s","-d","1","-p","0"],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        while True:
            r,_,_=select.select([p.stdout],[],[],3.0)
            if r:
                l=p.stdout.readline()
                if not l: break
                ll=l.lower()
                for k,c in M.items():
                    if k in ll: mc(c); break
    except: pass
    try: p.wait(timeout=2)
    except: p.kill()
    time.sleep(2)
'''
    _bridg=subprocess.Popen([sys.executable,"-c",sc],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {"ok":True,"pid":_bridg.pid}

def br_stop():
    global _bridg
    if _bridg and _bridg.poll() is None:
        _bridg.terminate()
        try: _bridg.wait(timeout=3)
        except: _bridg.kill()
    _bridg=None

def br_st():
    return {"on":_bridg is not None and _bridg.poll() is None,"pid":_bridg.pid if _bridg else None}

# ── Audio state/routing helpers ───────────────────────────────────────
USB_ALEXA_SRC="alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback"
BT_SOUNDBAR_MAC="24:4B:03:92:0B:8C"
BT_SOUNDBAR_NAME="[Samsung] Soundbar J-Series"
BT_SOUNDBAR_SINK="bluez_output.24_4B_03_92_0B_8C.1"
HDMI_SINK="alsa_output.platform-3f902000.hdmi.hdmi-stereo"
DLNA_SINK_KEYWORDS=["uuid_","WiiMu","LinkPlayer","Sphere","TIBO"]
AUDIO_LATENCY_FILE=os.path.expanduser("~/rpi-dashboard/.audio-latency.json")

def _run(cmd, t=5):
    return subprocess.run(cmd,capture_output=True,text=True,timeout=t)

def _pactl_lines(kind):
    r=_run(["pactl","list","short",kind])
    out=[]
    for l in r.stdout.strip().split("\n"):
        p=l.split()
        if len(p)>=2: out.append({"id":p[0],"name":p[1],"state":p[-1] if len(p)>4 else ""})
    return out

def _sink_volume(name):
    try:
        v=_run(["pactl","get-sink-volume",name]).stdout.strip()
        m=re.search(r"/(\s*\d+)%", v)
        return int(m.group(1)) if m else None
    except Exception: return None

def _source_volume(name):
    try:
        v=_run(["pactl","get-source-volume",name]).stdout.strip()
        m=re.search(r"/(\s*\d+)%", v)
        return int(m.group(1)) if m else None
    except Exception: return None

def _loopback_module_id():
    try:
        r=_run(["pactl","list","short","modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and USB_ALEXA_SRC in l and BT_SOUNDBAR_SINK in l:
                return l.split()[0]
    except Exception: pass
    return None

def _paired_bt_device(paired_text, mac=BT_SOUNDBAR_MAC):
    for line in (paired_text or "").splitlines():
        parts=line.split()
        if len(parts)>=3 and parts[0]=="Device" and parts[1].upper()==mac.upper():
            return {"paired": True, "mac": parts[1], "name": " ".join(parts[2:])}
    return {"paired": False, "mac": mac, "name": BT_SOUNDBAR_NAME}

def _classify_sink(name):
    n=name.lower()
    if "hdmi" in n: return "hdmi"
    if n.startswith("bluez_") or n.startswith("bluez_output"): return "bt"
    if any(kw.lower() in n for kw in DLNA_SINK_KEYWORDS) and "lg" not in n: return "dlna_output"
    if "usb" in n and "input" not in n: return "usb_output"
    return "other"

def _classify_source(name):
    n=name.lower()
    if "monitor" in n: return "monitor"
    if n.startswith(USB_ALEXA_SRC.lower()): return "usb_input"
    if "xing_wei" in n or "2.4g" in n: return "remote_input"
    if any(kw.lower() in n for kw in DLNA_SINK_KEYWORDS): return "dlna_input"
    return "other"

def _load_audio_latency():
    try:
        if os.path.exists(AUDIO_LATENCY_FILE):
            return json.load(open(AUDIO_LATENCY_FILE))
    except Exception: pass
    return {"dlna_output_offset_ms": 0, "default_latency_ms": 0}

def _save_audio_latency(data):
    try:
        json.dump(data, open(AUDIO_LATENCY_FILE, "w"))
    except Exception: pass

def _sink_input_streams():
    try:
        r=_run(["pactl","list","short","sink-inputs"])
        out=[]
        for l in r.stdout.strip().split("\n"):
            p=l.split()
            if len(p)>=3: out.append({"id":p[0],"sink":p[1],"client":p[2],"state":p[-1] if len(p)>5 else ""})
        return out
    except Exception: return []

def audio_state():
    sinks=_pactl_lines("sinks"); sources=_pactl_lines("sources")
    default_sink=_run(["pactl","get-default-sink"]).stdout.strip()
    default_source=_run(["pactl","get-default-source"]).stdout.strip()
    paired=_run(["bluetoothctl","devices","Paired"]).stdout.strip()
    soundbar=_paired_bt_device(paired)
    loop_id=_loopback_module_id()
    latency=_load_audio_latency()
    sink_inputs=_sink_input_streams()
    bt=next((s for s in sinks if s["name"]==BT_SOUNDBAR_SINK),None)
    hdmi=next((s for s in sinks if s["name"]==HDMI_SINK),None)
    usb_in=next((s for s in sources if s["name"]==USB_ALEXA_SRC),None)
    usb_out=next((s for s in sinks if "usb" in s["name"].lower() and "input" not in s["name"].lower()),None)
    dlna_out=next((s for s in sinks if _classify_sink(s["name"])=="dlna_output"),None)
    classified_sinks=[]
    for s in sinks:
        t=_classify_sink(s["name"])
        vol=_sink_volume(s["name"])
        classified_sinks.append({"id":s["id"],"name":s["name"],"type":t,"volume":vol,"state":s.get("state","")})
    order=["hdmi","bt","dlna_output","usb_output","other"]
    classified_sinks.sort(key=lambda x: order.index(x["type"]) if x["type"] in order else 99)
    classified_sources=[]
    for s in sources:
        t=_classify_source(s["name"])
        vol=_source_volume(s["name"])
        classified_sources.append({"id":s["id"],"name":s["name"],"type":t,"volume":vol,"state":s.get("state","")})
    return {
        "default_sink": default_sink,
        "default_source": default_source,
        "sinks": classified_sinks,
        "sources": classified_sources,
        "sink_inputs": sink_inputs,
        "devices": {
            "hdmi": {"present": bool(hdmi), "type": "hdmi", "name": HDMI_SINK, "volume": _sink_volume(HDMI_SINK) if hdmi else None, "state": hdmi.get("state") if hdmi else None},
            "bt_soundbar": {"present": bool(bt), "paired": soundbar["paired"], "mac": soundbar["mac"], "label": soundbar["name"], "type": "bt", "name": BT_SOUNDBAR_SINK, "volume": _sink_volume(BT_SOUNDBAR_SINK) if bt else None, "state": bt.get("state") if bt else None},
            "usb_alexa_input": {"present": bool(usb_in), "type": "usb_input", "name": USB_ALEXA_SRC, "volume": _source_volume(USB_ALEXA_SRC) if usb_in else None, "state": usb_in.get("state") if usb_in else None},
            "dlna_output": {"present": bool(dlna_out), "type": "dlna_output", "name": dlna_out["name"] if dlna_out else None, "volume": _sink_volume(dlna_out["name"]) if dlna_out else None, "state": dlna_out.get("state") if dlna_out else None},
            "usb_output": {"present": bool(usb_out), "type": "usb_output", "name": usb_out["name"] if usb_out else None, "volume": _sink_volume(usb_out["name"]) if usb_out else None, "state": usb_out.get("state") if usb_out else None},
        },
        "routes": {"alexa_to_bt": {"on": bool(loop_id), "module_id": loop_id, "ready": bool(bt and usb_in), "missing": {"bt_soundbar": not bool(bt), "usb_alexa_input": not bool(usb_in)}}},
        "bluetooth": {"soundbar": soundbar},
        "latency": latency,
        "paired_bt": paired,
    }

def audio_set_volume(kind, name, volume):
    if kind not in ("sink", "source"): return {"ok":False,"error":"kind must be sink or source"}
    if not name: return {"ok":False,"error":"name required"}
    vol=max(0, min(150, int(volume)))
    cmd=["pactl","set-"+kind+"-volume",name,str(vol)+"%"]
    r=_run(cmd, t=5)
    return {"ok":r.returncode==0,"kind":kind,"name":name,"volume":vol,"out":(r.stdout+r.stderr).strip()[:200]}

def audio_set_default(name):
    if not name: return {"ok":False,"error":"name required"}
    r=_run(["pactl","set-default-sink",name], t=5)
    return {"ok":r.returncode==0,"name":name,"out":(r.stdout+r.stderr).strip()[:200]}

def audio_set_latency(key, value_ms):
    lat=_load_audio_latency()
    lat[key]=int(value_ms)
    _save_audio_latency(lat)
    return {"ok":True,"latency":lat}

def audio_route_alexa_bt(action):
    if action=="stop":
        mid=_loopback_module_id()
        if mid: _run(["pactl","unload-module",mid])
        return {"ok":True,"route":"alexa_to_bt","on":False}
    if action=="start":
        if _loopback_module_id(): return {"ok":True,"route":"alexa_to_bt","on":True,"already":True}
        sources=_pactl_lines("sources")
        if not any(s["name"]==USB_ALEXA_SRC for s in sources):
            return {"ok":False,"route":"alexa_to_bt","on":False,"error":"USB Alexa input is not available"}
        # Ensure BT is connected and loud enough.
        subprocess.run(["bluetoothctl","connect",BT_SOUNDBAR_MAC],capture_output=True,text=True,timeout=10)
        time.sleep(1)
        sinks=_pactl_lines("sinks")
        if not any(s["name"]==BT_SOUNDBAR_SINK for s in sinks):
            return {"ok":False,"route":"alexa_to_bt","on":False,"error":"BT Soundbar sink is not available after connect attempt"}
        subprocess.run(["pactl","set-sink-volume",BT_SOUNDBAR_SINK,"100%"],capture_output=True)
        r=_run(["pactl","load-module","module-loopback",
                f"source={USB_ALEXA_SRC}",f"sink={BT_SOUNDBAR_SINK}","rate=48000","channels=2",
                "channel_map=front-left,front-right","source_dont_move=true","sink_dont_move=true","latency_msec=20","remix=true"], t=10)
        return {"ok":r.returncode==0,"route":"alexa_to_bt","on":r.returncode==0,"out":(r.stdout+r.stderr).strip()[:300]}
    return {"ok":False,"error":"bad action"}

# ── HTML ───────────────────────────────────────────────────────────────

CSS="""*{box-sizing:border-box}body{font-family:system-ui,sans-serif;max-width:860px;margin:0 auto;padding:.6rem;background:#0d1117;color:#c9d1d9;font-size:14px;overflow-x:hidden}
input,button,select{font-size:.9rem;padding:.5rem .65rem;margin:.1rem 0;border-radius:.3rem;border:1px solid #30363d;background:#161b22;color:#c9d1d9}
input,select{width:100%}button{cursor:pointer;background:#21262d}button:hover{background:#30363d;border-color:#58a6ff}
button:active{background:#1a5276}button.on{background:#1a5276;border-color:#58a6ff}button.danger{border-color:#f85149;color:#f85149}
.row{display:flex;gap:.3rem;flex-wrap:wrap;align-items:center}a{color:#58a6ff}
.tabs{display:flex;gap:0;margin-bottom:.4rem;border-bottom:1px solid #30363d}
.tab{padding:.45rem .9rem;background:transparent;color:#8b949e;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:.85rem}
.tab:hover{color:#c9d1d9}.tab.active{color:#58a6ff;border-bottom-color:#58a6ff}
.pnl{display:none;padding:.2rem 0}.pnl.active{display:block}
h1{margin:0 0 .2rem;font-size:1.2rem;color:#f0f6fc}
.sec{margin:.5rem 0;padding:.6rem;background:#161b22;border:1px solid #30363d;border-radius:.4rem}
.sec h3{margin:0 0 .3rem;font-size:.8rem;color:#8b949e}
.cec-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.2rem;max-width:240px;margin:.4rem 0}
.cec-grid button{font-size:1rem;padding:.5rem;text-align:center}
.vol-row{display:flex;gap:.2rem;max-width:240px;margin:.3rem 0}.vol-row button{flex:1}
select{max-width:120px;width:auto}
#toast{position:fixed;bottom:12px;right:12px;z-index:999;max-width:300px;display:flex;flex-direction:column;gap:4px;pointer-events:none}
.t{padding:.4rem .7rem;border-radius:.3rem;font-size:.8rem;pointer-events:auto;animation:fi .2s}
.t.ok{background:#0d2818;border:1px solid #238636;color:#3fb950}
.t.err{background:#3d1214;border:1px solid #da3633;color:#f85149}
.t.info{background:#0c2d6b;border:1px solid #1f6feb;color:#58a6ff}
@keyframes fi{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
pre{background:#161b22;padding:.6rem;border-radius:.3rem;overflow:auto;font-size:.8em;margin:.3rem 0}
#terminal{width:100%;max-width:100%;box-sizing:border-box;background:#000;padding:4px;border-radius:4px;height:420px;overflow:hidden}
#terminal .xterm{height:100%}
#terminal .xterm-viewport{overflow-y:hidden!important}
#terminal .xterm-screen{max-width:100%}
.media-head{display:flex;justify-content:space-between;gap:.6rem;align-items:center;margin:.3rem 0 .7rem}
.media-grid{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}
.media-card{background:#0d1117;border:1px solid #30363d;border-radius:.55rem;padding:.65rem;min-height:96px}
.media-card h4{margin:0 0 .4rem;font-size:.85rem;color:#f0f6fc;display:flex;justify-content:space-between;gap:.4rem}
.media-meta{font-size:.72rem;color:#8b949e;word-break:break-all;line-height:1.35}
.badge{display:inline-block;padding:.12rem .4rem;border-radius:999px;border:1px solid #30363d;font-size:.68rem;color:#8b949e}
.badge.ok{border-color:#238636;color:#3fb950;background:#0d2818}.badge.warn{border-color:#d29922;color:#d29922;background:#2d2308}.badge.err{border-color:#da3633;color:#f85149;background:#3d1214}
.meter{height:6px;background:#21262d;border-radius:999px;overflow:hidden;margin:.45rem 0}.meter span{display:block;height:100%;background:#58a6ff;width:0%}
.route-card{border-left:3px solid #58a6ff}.route-card.on{border-left-color:#3fb950}.route-card.off{border-left-color:#8b949e}
.vol-row-mixer{display:flex;align-items:center;gap:.3rem;margin:.25rem 0}.vol-row-mixer label{font-size:.72rem;color:#8b949e;min-width:48px;text-align:right}.vol-row-mixer input[type=range]{flex:1;height:6px;accent-color:#58a6ff;cursor:pointer}.vol-row-mixer button{font-size:.7rem;padding:2px 8px}
@media(max-width:700px){.media-grid{grid-template-columns:1fr}.media-head{flex-direction:column;align-items:flex-start}}"""

JS=r"""
function $(s){return document.querySelector(s)}function $$(s){return document.querySelectorAll(s)}
function msg(t,c){let d=document.createElement('div');d.className='t '+c;d.textContent=t;$('#toast').appendChild(d);setTimeout(()=>d.remove(),4000)}
async function api(u){try{return await(await fetch(u)).json()}catch(e){return{error:e.message}}}
function sw(n){$$('.tab').forEach(t=>t.classList.toggle('active',t.dataset.t===n));$$('.pnl').forEach(p=>p.classList.toggle('active',p.id==='p-'+n))}
async function play(){let u=$('#url').value.trim(),q=$('#qual').value;if(!u){msg('Enter URL','err');return}let r=await api('/mpv/play?url='+encodeURIComponent(u)+'&q='+q);if(r.error)msg(r.error,'err');else msg('Playing: '+(r.meta&&r.meta.title||r.q),'ok');setTimeout(st,1500)}
function pause(){api('/mpv/toggle').then(r=>msg(r.paused!==undefined?(r.paused?'Paused':'Playing'):'?','info'))}
function stop(){api('/mpv/stop').then(()=>{msg('Stopped','ok');$('#st').textContent='—'})}
function seek(d){api('/mpv/seek?d='+d)}
function vol(d){api('/mpv/vol?d='+d)}
let seeking=false,lastPos=0,lastDur=0;
function seekTo(v){if(lastDur>0){let pos=(v/100)*lastDur;api('/mpv/seekabs?pos='+pos.toFixed(1))}}
async function st(){let r=await api('/mpv/status'),s=$('#st');if(!r.on){s.textContent=r.err?'Error':'—';return}let p=fmt(r.pos),du=fmt(r.dur);s.innerHTML='<b>'+esc(r.title||'?')+'</b><br>'+p+'/'+du+(r.paused?' ⏸':'')+' Vol:'+Math.round(r.vol)+'% '+r.q;lastPos=r.pos||0;lastDur=r.dur||0;if(!seeking&&lastDur>0){let pct=(lastPos/lastDur)*100;$('#sbar').value=pct;$('#stime').textContent=fmt(lastPos);$('#dtime').textContent=fmt(lastDur)}}
function fmt(s){if(!s)return'0:00';let m=Math.floor(s/60),sc=Math.floor(s%60);return m+':'+(sc<10?'0':'')+sc}
function esc(s){return s?s.replace(/</g,'&lt;').replace(/>/g,'&gt;'):''}
function terminalActive(){let p=$('#p-terminal');let ae=document.activeElement;let t=document.getElementById('terminal');return !!((p&&p.classList.contains('active'))||(ae&&ae.closest&&(ae.closest('#terminal')||ae.closest('.xterm')||ae.classList.contains('xterm-helper-textarea')))||(t&&t.contains(ae)))}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.isContentEditable||terminalActive())return;switch(e.key){case'ArrowLeft':e.preventDefault();seek(-10);msg('⏪ -10s','info');break;case'ArrowRight':e.preventDefault();seek(10);msg('⏩ +10s','info');break;case'ArrowUp':e.preventDefault();vol(5);msg('🔊 +5%','info');break;case'ArrowDown':e.preventDefault();vol(-5);msg('🔉 -5%','info');break;case' ':return;case'MediaPlayPause':e.preventDefault();pause();msg('⏯ Play/Pause','info');break;case'MediaTrackNext':e.preventDefault();seek(30);msg('⏩ +30s','info');break;case'MediaTrackPrevious':e.preventDefault();seek(-30);msg('⏪ -30s','info');break;case'VolumeUp':e.preventDefault();vol(5);msg('🔊 +5%','info');break;case'VolumeDown':e.preventDefault();vol(-5);msg('🔉 -5%','info');break;case'AudioVolumeMute':e.preventDefault();api('/mpv/vol?d=-100');msg('🔇 Mute','info');break;case'f':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.25).toFixed(1));msg('⏪ 25%','info');break;case'g':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.5).toFixed(1));msg('⏩ 50%','info');break;case'h':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.75).toFixed(1));msg('⏩ 75%','info');break}})
function qu(u){$('#url').value=u;play()}
async function cec(c){msg('CEC: '+c,'info');let r=await api('/cec/send?c='+encodeURIComponent(c));msg(r.ok?'OK: '+c:(r.err||'fail'),r.ok?'ok':'err')}
async function cecKey(k){let r=await api('/cec/key?k='+encodeURIComponent(k));msg(r.ok?'OK: '+k:'fail',r.ok?'ok':'err')}
async function cecIn(n){let r=await api('/cec/in?n='+n);msg('HDMI '+n+': '+(r.ok?'ok':r.err||'?'),r.ok?'ok':'err')}
async function cecScan(){msg('Scanning CEC...','info');let r=await api('/cec/scan');$('#cdev').innerHTML='<pre>'+esc(r.out||r.err||'none')+'</pre>';msg(r.out?'Scan done':'No devices',r.out?'ok':'err')}
async function cecBr(){let s=await api('/cec/br/st');if(s.on){await api('/cec/br/stop');msg('Bridge off','info')}else{let r=await api('/cec/br/start');msg(r.ok?'Bridge ON':'fail',r.ok?'ok':'err')}updBr()}
async function updBr(){let r=await api('/cec/br/st'),b=$('#brb');if(r.on){b.textContent='⏹ Stop';b.className='on';$('#brs').textContent='ON — remote→mpv'}else{b.textContent='▶ Start';b.className='';$('#brs').textContent='OFF'}}
async function kPlay(){let u=$('#kurl').value.trim();if(!u)return;let r=await api('/play?url='+encodeURIComponent(u));msg(r.ok?'Kodi ✅':'⚠️',r.ok?'ok':'err')}
async function kStat(){let r=await api('/kodi/st');let p=r.result||[];$('#kst').textContent=p.length?'Player #'+p[0].playerid:'—'}
async function audio(t){let r=await api('/audio/'+t);msg(r.result||r.err,r.result?'ok':'err')}
async function devs(){
  let r=await api('/devices');let h='';
  if(r.hdmi&&r.hdmi.length)h+='<b>HDMI:</b> '+r.hdmi.join(', ')+'<br>';
  if(r.dlna&&r.dlna.length)h+='<b>DLNA:</b> '+r.dlna.join(', ')+'<br>';
  $('#dev').innerHTML=h||'—';
  // Paired + connected BT devices
  let bth='';
  if(r.bt&&r.bt.length){
    r.bt.forEach(d=>{
      let mac=d.match(/\(([0-9A-F:]{17})\)/i);
      let name=d.replace(/Paired: /,'').replace(/ \(.+\)/,'');
      let m=mac?mac[1]:'';
      bth+='<div style="margin:3px 0;display:flex;gap:4px;align-items:center">'+name+' <span style="color:#8b949e;font-size:.7em">'+m+'</span>';
      if(d.includes('BT (')){bth+=' <button onclick="btDisconnect(\''+m+'\')" style="font-size:.7em;padding:2px 6px"> Disconnect</button>';
      }else{bth+=' <button onclick="btConnect(\''+m+'\')" style="font-size:.7em;padding:2px 6px"> Connect</button>';
      bth+=' <button onclick="btRemove(\''+m+'\')" style="font-size:.7em;padding:2px 6px;color:#f85149"> Remove</button>';
      }
      bth+='</div>';
    });
  }
  $('#bt-list').innerHTML=bth||'—';
  $('#bt-status').textContent=r.bt?r.bt.length+' devices':'—'}
async function btScan(){
  msg('Scanning BT...','info');
  let r=await api('/bt/scan');
  let lines=(r.result||'').split('\n').filter(l=>l.startsWith('Device'));
  let h='';
  lines.forEach(l=>{
    let p=l.split(' ');
    if(p.length>=3){
      let mac=p[1];let name=p.slice(2).join(' ');
      h+='<div style="margin:3px 0;display:flex;gap:4px;align-items:center">'+name+' <span style="color:#8b949e;font-size:.7em">'+mac+'</span>';
      h+=' <button onclick="btPair(\''+mac+'\')" style="font-size:.7em;padding:2px 6px"> Pair</button>';
      h+=' <button onclick="btConnect(\''+mac+'\')" style="font-size:.7em;padding:2px 6px"> Connect</button>';
      h+='</div>';
    }
  });
  $('#bt-list').innerHTML=h||'No devices found';
  $('#bt-status').textContent=lines.length+' found';
  msg('Found '+lines.length+' devices','ok')}
async function btPair(mac){msg('Pairing '+mac+'...','info');let r=await api('/bt/pair?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(()=>devs(),2000)}
async function btConnect(mac){msg('Connecting '+mac+'...','info');let r=await api('/bt/connect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(()=>devs(),2000)}
async function btDisconnect(mac){msg('Disconnecting '+mac+'...','info');let r=await api('/bt/disconnect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(()=>devs(),2000)}
async function btRemove(mac){msg('Removing '+mac+'...','info');let r=await api('/bt/remove?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(()=>devs(),2000)}
async function btTrust(mac){msg('Trusting '+mac+'...','info');let r=await api('/bt/trust?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(()=>devs(),2000)}
async function dlnaScan(){msg('Scanning DLNA...','info');let r=await api('/dlna/scan');if(r.devices){let h=r.devices.map(d=>`<div>${d.usn.split('::')[0]} → ${d.location}</div>`).join('');$('#dlna-list').innerHTML=h;$('#dlna-status').textContent=r.count+' renderers';msg('Found '+r.count+' DLNA renderers','ok')}else{msg(r.error||'Scan failed','err')}}
function badge(on,label){return '<span class="badge '+(on?'ok':'err')+'">'+label+'</span>'}
function meter(v){let n=(v==null?0:v);return '<div class="meter"><span style="width:'+n+'%"></span></div><div class="media-meta">Volume: '+(v==null?'—':v+'%')+'</div>'}
function deviceCard(icon,title,d){let ok=d&&d.present;return '<div class="media-card"><h4>'+icon+' '+title+' '+badge(ok,ok?'ONLINE':'MISSING')+'</h4>'+meter(d&&d.volume)+'<div class="media-meta">'+esc((d&&d.name)||'not detected')+'<br>State: '+esc((d&&d.state)||'—')+'</div></div>'}
function btSoundbarCard(d){let ok=d&&d.present,paired=d&&d.paired;let h='<div class="media-card"><h4>🎧 BT Soundbar '+badge(ok,ok?'ONLINE':(paired?'PAIRED':'MISSING'))+'</h4>'+meter(d&&d.volume);h+='<div class="media-meta">'+esc((d&&d.label)||'Samsung Soundbar')+'<br>MAC: '+esc((d&&d.mac)||'—')+'<br>Sink: '+esc(ok?d.name:'not connected')+'<br>State: '+esc((d&&d.state)||'—')+'</div>';if(paired&&!ok)h+='<div class="row" style="margin-top:.45rem"><button onclick="taBtConnect(\''+esc(d.mac)+'\')">🔌 Connect Soundbar</button></div><div class="media-meta">Paired, but no PipeWire BT sink is currently available.</div>';return h+'</div>'}
async function taRefresh(){let r=await api('/audio/state');if(r.error){msg(r.error,'err');return}let d=r.devices||{};let sinks=r.sinks||[];let sources=r.sources||[];let inputs=r.sink_inputs||[];let lat=r.latency||{};let outHtml='';sinks.forEach(s=>{let icon=s.type==='hdmi'?'📺':(s.type==='bt'?'🎧':(s.type==='dlna_output'?'📡':(s.type==='usb_output'?'🔌':'🔊')));let title=s.type==='hdmi'?'HDMI':(s.type==='bt'?'BT Soundbar':(s.type==='dlna_output'?'DLNA Output':(s.type==='usb_output'?'USB Output':'Other')));outHtml+=deviceCard(icon,title,s)});$('#ta-sinks').innerHTML=outHtml;let srcHtml='';sources.forEach(s=>{let icon=s.type==='usb_input'?'🎙️':(s.type==='remote_input'?'🎮':(s.type==='dlna_input'?'📡':'🔊'));let title=s.type==='usb_input'?'Alexa USB Input':(s.type==='remote_input'?'Remote Mic':(s.type==='dlna_input'?'DLNA Input':'Other'));srcHtml+=deviceCard(icon,title,s)});srcHtml+='<div class="media-card"><h4>📡 DLNA '+badge(d.dlna_output&&d.dlna_output.present,'ACTIVE')+'</h4><div class="media-meta">DLNA render scan works. Rendering needs pa-dlna/rygel/Kodi.</div><div class="row" style="margin-top:.4rem"><button onclick="taDlnaScan()">🔍 Scan renderers</button><button onclick="taSwitch(\'dlna\')"'+(d.dlna_output&&d.dlna_output.present?' disabled title="Already active"':'')+'>📡 Switch to DLNA</button></div><div id="ta-dlna" class="media-meta" style="margin-top:.35rem">—</div></div>';$('#ta-sources').innerHTML=srcHtml;let mixerHtml='';if(inputs.length){inputs.forEach(i=>{mixerHtml+='<div class="media-card route-card"><h4>🎵 Stream → '+esc(i.sink)+' '+badge(i.state==='RUNNING','RUNNING')+'</h4><div class="media-meta">Client: '+esc(i.client)+'<br>State: '+esc(i.state)+'</div></div>'});}else{mixerHtml='<div class="media-card"><h4>🎵 Active Streams</h4><div class="media-meta">No active audio streams.</div></div>'}$('#ta-mixer').innerHTML=mixerHtml;let route=r.routes&&r.routes.alexa_to_bt;let ready=route&&route.ready;let warn=ready?'Ready.':'Needs online BT Soundbar and USB Alexa input before Start.';let startDisabled=ready?'':' disabled title="BT Soundbar or USB input missing"';$('#ta-routes').innerHTML='<div class="media-card route-card '+(route&&route.on?'on':'off')+'"><h4>🔁 Alexa AUX → BT Soundbar '+badge(route&&route.on,route&&route.on?'ON':(ready?'READY':'NOT READY'))+'</h4><div class="media-meta">USB C-Media mono input → PipeWire loopback → Samsung Soundbar A2DP<br>'+warn+'</div><div class="row" style="margin-top:.45rem"><button onclick="taRoute(\'start\')"'+startDisabled+'>▶ Start</button><button onclick="taRoute(\'stop\')" class="danger">⏹ Stop</button></div><div class="media-meta">Module: '+esc((route&&route.module_id)||'—')+'</div></div>';$('#ta-default').textContent=r.default_sink||'—';$('#ta-lat-dlna-offset').value=lat.dlna_output_offset_ms||0;$('#ta-raw').textContent=JSON.stringify(r,null,2)}
async function taRoute(a){let r=await api('/audio/route/alexa-bt?action='+a);msg(r.ok?'Route '+a+' OK':(r.error||r.out||'Route failed'),r.ok?'ok':'err');setTimeout(taRefresh,800)}
async function taBtConnect(mac){msg('Connecting Soundbar...','info');let r=await api('/bt/connect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(taRefresh,1500)}
async function taSwitch(t){let r=await api('/audio/'+t);msg(r.result||r.err,r.result?'ok':'err');setTimeout(taRefresh,800)}
async function taSetVol(kind,name,v){let r=await api('/audio/volume?kind='+kind+'&name='+encodeURIComponent(name)+'&volume='+v);msg(r.ok?'Volume → '+v+'%':(r.error||'fail'),r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taSetDefault(name){let r=await api('/audio/default-sink?name='+encodeURIComponent(name));msg(r.ok?'Default → '+name.split('.').pop():r.error||'fail',r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taSetLatency(key,v){let r=await api('/audio/latency?key='+key+'&value='+v);msg(r.ok?'Latency saved':r.error||'fail',r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taDlnaScan(){let r=await api('/dlna/scan');if(r.devices){$('#ta-dlna').innerHTML=r.devices.map(d=>'<div>'+esc(d.location||'')+'</div>').join('');msg('Found '+r.count+' renderers','ok')}else msg(r.error||'DLNA failed','err')}
async function launchApp(mode){msg('Launching '+mode+'...','info');let r=await fetch('http://192.168.0.205:8090/mode/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode})}).then(r=>r.json());msg(r.status?'OK: '+mode:(r.error||'fail'),r.status?'ok':'err')}
async function stopApp(){msg('Stopping...','info');let r=await fetch('http://192.168.0.205:8090/mode/stop',{method:'POST'}).then(r=>r.json());msg(r.message||'Stopped','ok')}
// Terminal
let term=null,termWs=null,termFit=null;
function termSendResize(){if(term&&termWs&&termWs.readyState===1){termWs.send(JSON.stringify({resize:{cols:term.cols,rows:term.rows}}))}}
function termFitNow(){if(termFit){termFit.fit();termSendResize()}}
function termInit(){if(term)return;term=new Terminal({theme:{background:'#0d1117',foreground:'#c9d1d9',cursor:'#58a6ff'},fontSize:13,fontFamily:'monospace',cursorBlink:true,scrollback:0,convertEol:true,disableStdin:false});termFit=new FitAddon.FitAddon();term.loadAddon(termFit);term.open(document.getElementById('terminal'));setTimeout(termFitNow,150);term.onData(d=>{if(termWs&&termWs.readyState===1)termWs.send(JSON.stringify({input:d}))});term.onResize(()=>termSendResize());window.addEventListener('resize',()=>setTimeout(termFitNow,100));msg('Terminal ready','info')}
function termDrawSnapshot(output,cursor){let row=1,col=1;if(cursor){row=Math.max(1,Math.min(term.rows,(cursor.y||0)+1));col=Math.max(1,Math.min(term.cols,(cursor.x||0)+1))}else{let lines=(output||'').split(/\r?\n/);let last=lines.length?lines[lines.length-1]:'';row=Math.max(1,Math.min(term.rows,lines.length));col=Math.max(1,Math.min(term.cols,(last||'').length+1))}term.write('\x1b[?25h\x1b[H\x1b[2J'+output+'\x1b['+row+';'+col+'H')}
function termConnect(){termInit();let host=location.hostname||'localhost';if(termWs&&termWs.readyState===1)return;termWs=new WebSocket('ws://'+host+':8098');termWs.onopen=()=>{msg('Connected','ok');$('#term-status').textContent='Connected';term.clear();termWs.send(JSON.stringify({action:'attach',session:'RPi',cols:term.cols,rows:term.rows}))};termWs.onmessage=e=>{try{let d=JSON.parse(e.data);if(d.full&&d.output!==undefined){termDrawSnapshot(d.output,d.cursor)}else if(d.output){term.write(d.output)}}catch{}};termWs.onclose=()=>{$('#term-status').textContent='Disconnected';msg('Disconnected','info')};termWs.onerror=()=>msg('Connection error','err')}
function termDisconnect(){if(termWs){termWs.close();termWs=null}$('#term-status').textContent='Disconnected'}
setInterval(()=>{st();updBr()},3000);kStat();devs();
"""

QO="\n".join(f'<option value="{k}"{" selected" if k==DQ else ""}>{k}</option>' for k in QUALITY)

def page():
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RPi-TV</title><style>{CSS}</style></head><body>
<h1>RPi-TV</h1><div id="toast"></div>
<div class="tabs">
<button class="tab active" data-t="player" onclick="sw('player')">🎬 Player</button>
<button class="tab" data-t="apps" onclick="sw('apps')">🚀 Apps</button>
<button class="tab" data-t="cec" onclick="sw('cec')">📺 CEC</button>
<button class="tab" data-t="kodi" onclick="sw('kodi')">📦 Kodi</button>
<button class="tab" data-t="audio" onclick="sw('audio')">🔊 Audio</button>
<button class="tab" data-t="testaudio" onclick="sw('testaudio');taRefresh()">🧪 Test Audio</button>
<button class="tab" data-t="terminal" onclick="sw('terminal')">💻 Terminal</button></div>
<div id="p-player" class="pnl active"><div class="sec">
<div class="row"><input id="url" placeholder="YouTube or direct URL..." style="flex:1"><select id="qual">{QO}</select></div>
<div class="row" style="margin-top:.3rem">
<button onclick="play()">▶ Play</button><button onclick="pause()">⏸</button><button onclick="stop()" class="danger">⏹</button>
<button onclick="seek(-10)">⏪10</button><button onclick="seek(10)">10⏩</button>
<button onclick="vol(-10)">🔉</button><button onclick="vol(10)">🔊</button></div>
<div style="margin-top:.4rem"><div style="display:flex;align-items:center;gap:.4rem"><span id="stime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span><input type="range" id="sbar" min="0" max="100" value="0" step="0.1" style="flex:1;height:6px;accent-color:#58a6ff;cursor:pointer" oninput="seekTo(this.value)" ontouchstart="seeking=true" ontouchend="seeking=false"><span id="dtime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span></div></div></div>
<div class="sec"><h3>Status</h3><div id="st">—</div></div>
<div class="sec"><h3>Quick</h3><div class="row">
<button onclick="qu('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" style="font-size:.75rem">🎵 Rick Astley</button>
<button onclick="qu('https://www.youtube.com/watch?v=9bZkp7q19f0')" style="font-size:.75rem">🎵 Gangnam</button></div></div></div>
</div>
<div id="p-apps" class="pnl"><div class="sec"><h3>Spustit aplikaci</h3>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:.5rem">
<button onclick="launchApp('steamlink')" style="padding:12px;font-size:1rem">🎮 Steam Link</button>
<button onclick="launchApp('gfn')" style="padding:12px;font-size:1rem">🎯 GeForce Now</button>
<button onclick="launchApp('mpv')" style="padding:12px;font-size:1rem">🎬 MPV Přehrávač</button>
<button onclick="launchApp('spotify')" style="padding:12px;font-size:1rem">🎵 Spotify</button>
<button onclick="launchApp('amazon')" style="padding:12px;font-size:1rem">🎶 Amazon Music</button>
<button onclick="stopApp()" style="padding:12px;font-size:1rem;color:#f85149;border:2px solid #f85149">⏹ ZASTAVIT & VRÁTIT SE</button>
</div></div>
<div class="sec"><h3>Návrat do Dashboardu</h3>
<div style="font-size:.85em;color:#c9d1d9">
• <b>Ctrl+C</b> — ukončí většinu aplikací<br>
• <b>Ctrl+Q</b> — ukončí Steam Link<br>
• <b>tlačítko ZASTAVIT</b> — vynutí návrat<br>
• Aplikace běží přímo na TV, dashboard se automaticky vrátí po ukončení
</div></div></div>
<div id="p-cec" class="pnl"><div class="sec"><h3>Power</h3><div class="row">
<button onclick="cec('on 0')">🟢 On</button><button onclick="cec('standby 0')" class="danger">🔴 Off</button>
<button onclick="cecScan()">🔍 Scan</button></div></div>
<div class="sec"><h3>Remote→MPV Bridge</h3><div class="row">
<button id="brb" onclick="cecBr()">▶ Start</button><span id="brs" style="font-size:.75em;color:#8b949e">OFF</span></div>
<div style="font-size:.7em;color:#666">Play/Pause, Stop, Seek, Vol via TV remote</div></div>
<div class="sec"><h3>Nav</h3><div class="cec-grid">
<button onclick="cecKey('menu')">📋</button><button onclick="cecKey('up')">▲</button><button onclick="cecKey('channels+')">CH+</button>
<button onclick="cecKey('left')">◀</button><button onclick="cecKey('select')" style="font-size:.7rem">OK</button><button onclick="cecKey('right')">▶</button>
<button onclick="cecKey('back')">◀◀</button><button onclick="cecKey('down')">▼</button><button onclick="cecKey('channels-')">CH-</button></div></div>
<div class="sec"><h3>Vol</h3><div class="vol-row">
<button onclick="cec('voldown')">🔉−</button><button onclick="cec('mute')">🔇</button><button onclick="cec('volup')">🔊+</button></div></div>
<div class="sec"><h3>Input</h3><div class="row">
<button onclick="cecIn(1)">HDMI1</button><button onclick="cecIn(2)">HDMI2</button><button onclick="cecIn(3)">HDMI3</button></div></div>
<div class="sec"><h3>Devices</h3><div id="cdev" style="font-size:.8em;color:#8b949e">Click Scan</div></div></div>
<div id="p-kodi" class="pnl"><div class="sec">
<div class="row"><input id="kurl" placeholder="URL for Kodi..." style="flex:1"><button onclick="kPlay()">▶ Kodi</button></div>
<div id="kst" style="font-size:.8em;color:#8b949e;margin-top:.2rem">—</div></div></div>
<div id="p-audio" class="pnl"><div class="sec"><div class="row">
<button onclick="audio('bt')">🔊 BT</button><button onclick="audio('hdmi')">🔊 HDMI</button><button onclick="audio('dlna')">🔊 DLNA (WiiMu)</button>
<button onclick="if(confirm('Reboot RPi?'))fetch('/system/reboot').then(r=>r.json()).then(j=>msg(j.out,'info'))" class="danger">🔄 Reboot</button></div></div>
<div class="sec"><h3>Zařízení</h3><div id="dev" style="font-size:.8em;color:#8b949e">—</div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem">
<div class="sec"><h3>Bluetooth</h3>
<div class="row" style="margin-bottom:.4rem"><button onclick="btScan()">🔍 Scan</button><span id="bt-status" style="font-size:.75em;color:#8b949e">—</span></div>
<div id="bt-list" style="font-size:.8em;color:#8b949e">Klikni Scan</div></div>
<div class="sec"><h3>DLNA</h3>
<div class="row" style="margin-bottom:.4rem"><button onclick="dlnaScan()">🔍 Scan</button><span id="dlna-status" style="font-size:.75em;color:#8b949e">—</span></div>
<div id="dlna-list" style="font-size:.8em;color:#8b949e">Klikni Scan</div></div>
</div></div>
<div id="p-testaudio" class="pnl">
<div class="sec"><div class="media-head"><div><h3>Audio & Media Prototype</h3><div class="media-meta">Safe prototype. Original Audio tab is untouched.</div></div><div class="row"><button onclick="taRefresh()">🔄 Refresh</button><button onclick="taSwitch('bt')">🎧 BT</button><button onclick="taSwitch('hdmi')">📺 HDMI</button><button onclick="taSwitch('dlna')">📡 DLNA</button></div></div><div class="media-meta">Default sink: <span id="ta-default">—</span></div></div>
<div class="media-grid"><div><div class="sec"><h3>Output Sinks</h3><div id="ta-sinks" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div><div><div class="sec"><h3>Input Sources</h3><div id="ta-sources" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div></div>
<div class="sec"><h3>Mixer — Active Streams</h3><div id="ta-mixer" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3>Audio Routing</h3><div id="ta-routes" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3>DLNA Latency Compensation</h3><div style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">
<label style="font-size:.72rem;color:#8b949e">DLNA Output offset (ms):</label>
<input type="number" id="ta-lat-dlna-offset" value="0" min="-2000" max="5000" step="50" style="width:80px">
<button onclick="taSetLatency('dlna_output_offset_ms',$('#ta-lat-dlna-offset').value)">💾 Save</button>
<span class="media-meta">Positive = delay output. Applied by renderer when available.</span></div></div>
<div class="sec"><h3>Diagnostics</h3><pre id="ta-raw">Click Refresh</pre></div>
</div>
<div id="p-terminal" class="pnl"><div class="sec">
<div class="row" style="margin-bottom:.4rem"><button onclick="termConnect()">🔌 Connect</button><button onclick="termDisconnect()" class="danger">⏹ Disconnect</button><span id="term-status" style="font-size:.75em;color:#8b949e">Disconnected</span></div>
<div id="terminal"></div></div></div>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
<script>{JS}</script></body></html>"""


class H(BaseHTTPRequestHandler):
    server_version="RPi-TV/4.2"
    def log_message(self,f,*a): pass
    def sj(self,c,o):
        d=json.dumps(o,ensure_ascii=False).encode()
        self.send_response(c);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(d)));self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers();self.wfile.write(d)
    def st(self,c,b,ct="text/html;charset=utf-8"):
        d=b.encode()
        self.send_response(c);self.send_header("Content-Type",ct)
        self.send_header("Content-Length",str(len(d)));self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers();self.wfile.write(d)
    def do_GET(self):
        p=urlparse(self.path);q=parse_qs(p.query);path=p.path
        try:
            if path in ("/","/index.html"): return self.st(200,page())
            elif path=="/favicon.ico": return self.st(204,"","image/x-icon")
            elif path=="/mpv/play":
                u=(q.get("url")or[""])[0].strip();ql=(q.get("q")or[None])[0]
                if not u: return self.sj(400,{"error":"no url"})
                self.sj(200,mpv_start(u,ql))
            elif path=="/mpv/stop": mpv_stop();self.sj(200,{"ok":True})
            elif path=="/mpv/toggle":
                mcmd("cycle","pause");s=mget("pause")
                self.sj(200,{"ok":True,"paused":s.get("data",False)})
            elif path=="/mpv/status": self.sj(200,mpv_st())
            elif path=="/mpv/seek":
                d=(q.get("d")or["10"])[0];mcmd("seek",float(d),"relative");self.sj(200,{"ok":True})
            elif path=="/mpv/seekabs":
                pos=(q.get("pos")or["0"])[0];mcmd("seek",float(pos),"absolute");self.sj(200,{"ok":True})
            elif path=="/mpv/vol":
                d=(q.get("d")or["10"])[0];mcmd("add","volume",int(d));self.sj(200,{"ok":True})
            elif path=="/cec/send":
                c=(q.get("c")or[""])[0].strip()
                if not c: return self.sj(400,{"error":"no cmd"})
                self.sj(200,cec_cmd(c))
            elif path=="/cec/key":
                k=(q.get("k")or[""])[0].strip()
                if not k: return self.sj(400,{"error":"no key"})
                self.sj(200,cec_cmd(f"user-control pressed '{k}'"))
            elif path=="/cec/in":
                n=(q.get("n")or["1"])[0]
                # Send active-source to request TV to switch to our input
                self.sj(200,cec_cmd(f"active-source phys-addr=1.0.0.0"))
            elif path=="/cec/scan": self.sj(200,{"ok":True,"out":cec_scan()})
            elif path=="/cec/br/start": self.sj(200,br_start())
            elif path=="/cec/br/stop": br_stop();self.sj(200,{"ok":True})
            elif path=="/cec/br/st": self.sj(200,br_st())
            elif path=="/play":
                u=(q.get("url")or[""])[0].strip()
                if not u: return self.sj(400,{"error":"no url"})
                su,me=resolve(u);r=kodi_rpc("Player.Open",{"item":{"file":su}})
                self.sj(200,{"ok":True,"url":su,"meta":me,"kodi":r})
            elif path=="/kodi/st": self.sj(200,kodi_rpc("Player.GetActivePlayers"))
            elif path=="/audio/state": self.sj(200,audio_state())
            elif path=="/audio/volume":
                kind=(q.get("kind")or[""])[0].strip()
                name=(q.get("name")or[""])[0].strip()
                vol=(q.get("volume")or["100"])[0].strip()
                self.sj(200,audio_set_volume(kind,name,vol))
            elif path=="/audio/default-sink":
                name=(q.get("name")or[""])[0].strip()
                self.sj(200,audio_set_default(name))
            elif path=="/audio/latency":
                key=(q.get("key")or[""])[0].strip()
                value=(q.get("value")or["0"])[0].strip()
                self.sj(200,audio_set_latency(key,value))
            elif path=="/audio/route/alexa-bt":
                a=(q.get("action")or["status"])[0].strip()
                if a=="status": return self.sj(200,{"ok":True,"route":"alexa_to_bt","on":bool(_loopback_module_id()),"module_id":_loopback_module_id()})
                self.sj(200,audio_route_alexa_bt(a))
            elif path=="/audio/bt":
                o=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True)
                sinks=[l.split()[1] for l in o.stdout.strip().split('\n') if len(l.split())>1]
                bt=next((s for s in sinks if s.startswith("bluez_sink") or s.startswith("bluez_output")),None)
                if bt:
                    subprocess.run(["pactl","set-default-sink",bt],capture_output=True)
                    self.sj(200,{"result":f"BT → {bt}"})
                else:
                    paired=subprocess.run(["bluetoothctl","devices","Paired"],capture_output=True,text=True)
                    self.sj(200,{"result":"No BT sink. Paired: "+paired.stdout.strip()[:200]})
            elif path=="/audio/hdmi":
                subprocess.run(["pactl","set-default-sink","alsa_output.platform-3f902000.hdmi.hdmi-stereo"],capture_output=True)
                subprocess.run(["pactl","set-sink-mute","alsa_output.platform-3f902000.hdmi.hdmi-stereo","0"],capture_output=True)
                self.sj(200,{"result":"HDMI set"})
            elif path=="/audio/dlna":
                o=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True)
                sinks=[l.split()[1] for l in o.stdout.strip().split('\n') if len(l.split())>1]
                dlna=next((s for s in sinks if ("uuid_" in s or "WiiMu" in s or "LinkPlayer" in s or "Sphere" in s) and "LG" not in s),None)
                if dlna:
                    subprocess.run(["pactl","set-default-sink",dlna],capture_output=True)
                    self.sj(200,{"result":f"DLNA → {dlna}"})
                else:
                    self.sj(200,{"result":"No DLNA sink. Available: "+', '.join(sinks)})
            elif path=="/devices":
                o=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True)
                sinks=[l.split()[1] for l in o.stdout.strip().split('\n') if len(l.split())>1]
                bt,dlna,hdmi=[],[],[]
                for s in sinks:
                    if s.startswith("bluez_sink") or s.startswith("bluez_output"): bt.append(f"BT ({s.split('.')[1].replace('_',':')})")
                    elif "-uuid_" in s and "LG" not in s: dlna.append(f"DLNA ({s})")
                    elif "hdmi" in s.lower(): hdmi.append(f"HDMI ({s})")
                paired=subprocess.run(["bluetoothctl","devices","Paired"],capture_output=True,text=True)
                for line in paired.stdout.strip().split('\n'):
                    if line.startswith("Device"):
                        parts=line.split()
                        if len(parts)>=3:
                            name=' '.join(parts[2:])
                            bt.append(f"Paired: {name} ({parts[1]})")
                self.sj(200,{"bt":bt,"dlna":dlna,"hdmi":hdmi})
            elif path=="/bt/scan":
                # Start scan in background, return immediately
                subprocess.Popen(["bluetoothctl","scan","on"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                import time; time.sleep(5)
                subprocess.run(["bluetoothctl","scan","off"],capture_output=True,text=True,timeout=3)
                devs=subprocess.run(["bluetoothctl","devices"],capture_output=True,text=True,timeout=3)
                self.sj(200,{"result":devs.stdout.strip()[:800] or "No devices"})
            elif path=="/dlna/scan":
                try:
                    r=subprocess.run(["gssdp-discover","-n","5","-t","urn:schemas-upnp-org:device:MediaRenderer:1"],capture_output=True,text=True,timeout=10)
                    # Parse output for MediaRenderer devices
                    lines=r.stdout.strip().split('\n')
                    devices=[]
                    current={}
                    for l in lines:
                        l=l.strip()
                        if l.startswith("resource available"):
                            if current: devices.append(current)
                            current={}
                        elif l.startswith("USN:"):
                            current["usn"]=l[4:].strip()
                        elif l.startswith("Location:"):
                            current["location"]=l[8:].strip()
                    if current: devices.append(current)
                    # Filter MediaRenderer
                    renderers=[d for d in devices if "MediaRenderer" in d.get("usn","")]
                    self.sj(200,{"devices":renderers,"count":len(renderers)})
                except Exception as e:
                    self.sj(200,{"error":str(e)})
            elif path=="/bt/trust":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","trust",mac],capture_output=True,text=True,timeout=5)
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300]})
            elif path=="/bt/pair":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","pair",mac],capture_output=True,text=True,timeout=15)
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300]})
            elif path=="/bt/connect":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","connect",mac],capture_output=True,text=True,timeout=10)
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300]})
            elif path=="/bt/disconnect":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","disconnect",mac],capture_output=True,text=True,timeout=5)
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300]})
            elif path=="/bt/remove":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","remove",mac],capture_output=True,text=True,timeout=5)
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300]})
            elif path=="/system/reboot":
                subprocess.run(["sudo","reboot"],capture_output=True)
                self.sj(200,{"ok":True,"out":"Rebooting..."})
            else: self.st(404,"nf","text/plain")
        except Exception as e: self.sj(500,{"error":str(e)})
    def do_POST(self):
        ln=int(self.headers.get("Content-Length","0"))
        body=self.rfile.read(ln).decode()
        u=(parse_qs(body).get("url")or[""])[0].strip()
        if not u: return self.st(400,page())
        try:
            su,me=resolve(u);r=kodi_rpc("Player.Open",{"item":{"file":su}})
            self.sj(200,{"ok":True,"url":su,"meta":me,"kodi":r})
        except Exception as e: self.sj(500,{"error":str(e)})

# ── Terminal WebSocket Server ─────────────────────────────────────────
WS_PORT = 8098

async def term_handler(websocket):
    session_name = "RPi:0"
    rows = 24
    cols = 80
    poll_task = None

    def resize_tmux():
        try:
            subprocess.run(["tmux", "resize-pane", "-t", session_name, "-x", str(cols), "-y", str(rows)],
                capture_output=True, timeout=1)
        except Exception:
            pass

    async def poll_output():
        while True:
            await asyncio.sleep(0.35)
            try:
                content = subprocess.run(["tmux", "capture-pane", "-t", session_name, "-p", "-S", f"-{rows}"],
                    capture_output=True, text=True, timeout=2).stdout
                cursor_raw = subprocess.run(["tmux", "display-message", "-t", session_name, "-p", "#{cursor_x} #{cursor_y}"],
                    capture_output=True, text=True, timeout=1).stdout.strip().split()
                cursor_x = int(cursor_raw[0]) if len(cursor_raw) >= 1 and cursor_raw[0].isdigit() else 0
                cursor_y = int(cursor_raw[1]) if len(cursor_raw) >= 2 and cursor_raw[1].isdigit() else 0
                lines = content.splitlines()[-rows:]
                normalized = "\r\n".join(line[:cols] for line in lines)
                await websocket.send(json.dumps({"output": normalized, "full": True, "cursor": {"x": cursor_x, "y": cursor_y}}))
            except Exception:
                break

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception:
                continue
            if data.get("action") == "attach":
                session_name = data.get("session", "RPi")
                rows = max(10, min(80, int(data.get("rows") or rows)))
                cols = max(40, min(160, int(data.get("cols") or cols)))
                resize_tmux()
                if poll_task:
                    poll_task.cancel()
                poll_task = asyncio.create_task(poll_output())
            elif data.get("resize"):
                r = data.get("resize") or {}
                rows = max(10, min(80, int(r.get("rows") or rows)))
                cols = max(40, min(160, int(r.get("cols") or cols)))
                resize_tmux()
            elif data.get("input"):
                try:
                    inp = data["input"]
                    special_keys = {
                        "\r": "Enter",
                        "\n": "Enter",
                        "\x7f": "BSpace",
                        "\b": "BSpace",
                        "\t": "Tab",
                        "\x03": "C-c",
                        "\x04": "C-d",
                        "\x1b[A": "Up",
                        "\x1b[B": "Down",
                        "\x1b[C": "Right",
                        "\x1b[D": "Left",
                        "\x1b[3~": "Delete",
                        "\x1b[H": "Home",
                        "\x1b[F": "End",
                    }
                    if inp in special_keys:
                        subprocess.run(["tmux", "send-keys", "-t", session_name, special_keys[inp]],
                            capture_output=True, timeout=1)
                    else:
                        subprocess.run(["tmux", "send-keys", "-t", session_name, "-l", inp],
                            capture_output=True, timeout=1)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        if poll_task:
            poll_task.cancel()

def start_ws_server():
    if not HAS_WS:
        print("[WARN] websockets not installed, terminal disabled", file=sys.stderr)
        return
    async def run():
        async with websockets.serve(term_handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()  # run forever
    def thread():
        asyncio.run(run())
    t = threading.Thread(target=thread, daemon=True)
    t.start()
    print(f"Terminal WS on ws://0.0.0.0:{WS_PORT}", flush=True)

def mpv_ipc_socket_live(path=MSOCK):
    """Return True when an existing mpv IPC socket accepts commands.

    This protects active playback during webserver restarts. Never unlink a
    live mpv socket, otherwise the video may keep playing but WebUI loses
    control of it.
    """
    if not os.path.exists(path) or not stat.S_ISSOCK(os.stat(path).st_mode):
        return False
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        s.settimeout(0.8)
        s.connect(path)
        s.sendall(b'{"command":["get_property","pause"]}\n')
        data=s.recv(4096)
        s.close()
        return b'"error":"success"' in data or b'"data"' in data
    except Exception:
        return False

def cleanup_stale_mpv_socket():
    if not os.path.exists(MSOCK):
        return
    if mpv_ipc_socket_live(MSOCK):
        print(f"Preserving live mpv IPC socket: {MSOCK}", flush=True)
        return
    try:
        os.unlink(MSOCK)
        print(f"Removed stale mpv IPC socket: {MSOCK}", flush=True)
    except Exception as e:
        print(f"[WARN] Could not remove stale mpv IPC socket {MSOCK}: {e}", file=sys.stderr, flush=True)

if __name__=="__main__":
    cleanup_stale_mpv_socket()
    start_ws_server()
    httpd=ThreadingHTTPServer((HOST,PORT),H)
    print(f"RPi-TV on http://{HOST}:{PORT}",flush=True)
    httpd.serve_forever()
