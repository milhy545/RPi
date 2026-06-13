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
    _opts={"quiet":True,"no_warnings":True,"noplaylist":True,"format":fmt,
           "extractor_args":{"youtube":{"player_client":["default","android","web"]}}}
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
SILENT_WAV="/tmp/rpi-silent-48k.wav"
PA_DLNA_LOG="/tmp/pa-dlna-webui.log"
_PA_DLNA_PORT="8088"
_pa_dlna_proc=None
_ka_procs={}  # sink_name -> subprocess.Popen
_audio_state_cache={"ts": 0.0, "data": None}
_audio_state_lock=threading.Lock()
AUDIO_STATE_CACHE_TTL=0.75


def _run(cmd, t=5):
    return subprocess.run(cmd,capture_output=True,text=True,timeout=t)

def _parse_int(value, field):
    try:
        return int(str(value).strip()), None
    except (TypeError, ValueError):
        return None, {"ok": False, "error": f"{field} must be an integer"}

def _pactl_lines(kind):
    r=_run(["pactl","list","short",kind])
    out=[]
    for l in r.stdout.strip().split("\n"):
        if not l.strip(): continue
        # pactl uses tabs as column separators: ID<TAB>NAME<TAB>DRIVER<TAB>SAMPLE_SPEC<TAB>STATE
        # Name may contain spaces but NOT tabs, so split on tab is safe
        p=l.split("\t")
        if len(p)<5: continue
        out.append({"id":p[0].strip(),"name":p[1].strip(),"state":p[-1].strip()})
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

def _sink_name_by_id(sink_id, sinks):
    for s in sinks:
        if str(s["id"])==str(sink_id): return s["name"]
    return None

def _sink_input_streams(sinks=None):
    try:
        r=_run(["pactl","list","short","sink-inputs"])
        out=[]
        for l in r.stdout.strip().split("\n"):
            p=l.split()
            if len(p)>=3:
                sink_id=p[1]
                client_pid=p[2]
                if sink_id=="4294967295": continue  # skip unrouted
                sink_label=_sink_name_by_id(sink_id, sinks) if sinks else None
                if not sink_label: continue
                out.append({"id":p[0],"sink_id":sink_id,"sink":sink_label,"client":client_pid,"format":p[4] if len(p)>4 else ""})
        return out
    except Exception: return []

def _audio_state_uncached():
    sinks=_pactl_lines("sinks"); sources=_pactl_lines("sources")
    default_sink=_run(["pactl","get-default-sink"]).stdout.strip()
    default_source=_run(["pactl","get-default-source"]).stdout.strip()
    paired=_run(["bluetoothctl","devices","Paired"]).stdout.strip()
    soundbar=_paired_bt_device(paired)
    loop_id=_loopback_module_id()
    latency=_load_audio_latency()
    sink_inputs=_sink_input_streams(sinks)
    bt=next((s for s in sinks if s["name"]==BT_SOUNDBAR_SINK),None)
    hdmi=next((s for s in sinks if s["name"]==HDMI_SINK),None)
    usb_in=next((s for s in sources if s["name"]==USB_ALEXA_SRC),None)
    usb_out=next((s for s in sinks if "usb" in s["name"].lower() and "input" not in s["name"].lower()),None)
    dlna_out=next((s for s in sinks if _classify_sink(s["name"])=="dlna_output"),None)
    classified_sinks=[]
    for s in sinks:
        t=_classify_sink(s["name"])
        if t=="other": continue
        vol=_sink_volume(s["name"])
        classified_sinks.append({"id":s["id"],"name":s["name"],"type":t,"present":True,"volume":vol,"state":s.get("state","")})
    order=["hdmi","bt","dlna_output","usb_output"]
    classified_sinks.sort(key=lambda x: order.index(x["type"]) if x["type"] in order else 99)
    classified_sources=[]
    for s in sources:
        t=_classify_source(s["name"])
        if t=="monitor": continue
        vol=_source_volume(s["name"])
        classified_sources.append({"id":s["id"],"name":s["name"],"type":t,"present":True,"volume":vol,"state":s.get("state","")})
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
        "dlna_connected": _pa_dlna_running(),
        "keepalive": _keepalive_status(),
    }

def audio_state(force=False):
    """Return cached audio state briefly to avoid repeated pactl/bluetooth pressure."""
    now=time.monotonic()
    with _audio_state_lock:
        cached=_audio_state_cache.get("data")
        if (not force) and cached is not None and now-_audio_state_cache.get("ts",0) < AUDIO_STATE_CACHE_TTL:
            data=json.loads(json.dumps(cached))
            data["cache"]={"hit": True, "ttl_ms": int(AUDIO_STATE_CACHE_TTL*1000)}
            return data
        data=_audio_state_uncached()
        _audio_state_cache["ts"]=time.monotonic()
        _audio_state_cache["data"]=json.loads(json.dumps(data))
        data["cache"]={"hit": False, "ttl_ms": int(AUDIO_STATE_CACHE_TTL*1000)}
        return data


def audio_set_volume(kind, name, volume):
    if kind not in ("sink", "source"): return {"ok":False,"error":"kind must be sink or source"}
    if not name: return {"ok":False,"error":"name required"}
    vol, err = _parse_int(volume, "volume")
    if err: return err
    vol=max(0, min(150, vol))
    cmd=["pactl","set-"+kind+"-volume",name,str(vol)+"%"]
    r=_run(cmd, t=5)
    return {"ok":r.returncode==0,"kind":kind,"name":name,"volume":vol,"out":(r.stdout+r.stderr).strip()[:200]}

def audio_set_default(name):
    if not name: return {"ok":False,"error":"name required"}
    r=_run(["pactl","set-default-sink",name], t=5)
    return {"ok":r.returncode==0,"name":name,"out":(r.stdout+r.stderr).strip()[:200]}

def _apply_dlna_delay():
    """Apply saved DLNA latency offset as mpv audio-delay (in seconds)."""
    lat=_load_audio_latency()
    offset_ms=lat.get("dlna_output_offset_ms",0)
    offset_s=offset_ms/1000.0
    r=mcmd("set_property","audio-delay",offset_s)
    return {"ok":r.get("error")=="success","offset_ms":offset_ms,"mpv":r}

def _reset_dlna_delay():
    """Reset mpv audio-delay to 0 (call when DLNA disconnects)."""
    return mcmd("set_property","audio-delay",0.0)

def audio_set_latency(key, value_ms):
    if key not in ("dlna_output_offset_ms", "default_latency_ms"):
        return {"ok":False,"error":"invalid latency key"}
    value, err = _parse_int(value_ms, "value")
    if err: return err
    value=max(-5000, min(5000, value))
    lat=_load_audio_latency()
    lat[key]=value
    _save_audio_latency(lat)
    if key=="dlna_output_offset_ms" and _pa_dlna_running():
        _apply_dlna_delay()
    return {"ok":True,"latency":lat}

def _ensure_silent_wav():
    if os.path.exists(SILENT_WAV): return
    import struct, wave
    f=wave.open(SILENT_WAV,'w')
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000)
    f.writeframes(struct.pack('<'+'h'*48000, *([0]*48000)))
    f.close()

def _keepalive_start(sink_name):
    global _ka_procs
    if sink_name in _ka_procs and _ka_procs[sink_name].poll() is None: return True
    _ensure_silent_wav()
    try:
        proc=subprocess.Popen(
            ["bash","-c",'while true; do pw-cat -p --target "$1" --format s16le --rate 48000 --channels 1 "$2" 2>/dev/null; sleep 0.5; done',
             "rpi-keepalive", sink_name, SILENT_WAV],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _ka_procs[sink_name]=proc
        return True
    except Exception: return False

def _keepalive_stop(sink_name=None):
    global _ka_procs
    if sink_name:
        proc=_ka_procs.pop(sink_name, None)
        if proc and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=3)
            except: proc.kill()
        return True
    for sn in list(_ka_procs):
        _keepalive_stop(sn)
    return True

def _keepalive_orphans():
    out=[]
    try:
        r=_run(["ps","-eo","pid=,ppid=,args="], t=3)
        for line in r.stdout.splitlines():
            if "pw-cat -p --target" not in line or SILENT_WAV not in line:
                continue
            m=re.match(r"\s*(\d+)\s+(\d+)\s+(.*)$", line)
            if not m: continue
            args=m.group(3)
            tm=re.search(r'--target "([^"]+)"', args) or re.search(r'--target\s+(.+?)\s+--format', args)
            target=tm.group(1).strip() if tm else "unknown"
            if target in ('"$1"', '$1', "unknown") and "rpi-keepalive" in args:
                km=re.search(r'rpi-keepalive\s+(\S+)\s+'+re.escape(SILENT_WAV), args)
                if km: target=km.group(1).strip()
            out.append({"pid": int(m.group(1)), "ppid": int(m.group(2)), "target": target})
    except Exception:
        pass
    return out

def _stop_keepalive_orphans():
    killed=[]
    for item in _keepalive_orphans():
        for pid in (item.get("pid"), item.get("ppid")):
            if not pid or pid == os.getpid() or pid in killed:
                continue
            try:
                os.kill(pid, 15)
                killed.append(pid)
            except ProcessLookupError:
                pass
            except Exception:
                pass
    time.sleep(0.2)
    for item in _keepalive_orphans():
        for pid in (item.get("pid"), item.get("ppid")):
            if not pid or pid == os.getpid():
                continue
            try:
                os.kill(pid, 9)
                if pid not in killed: killed.append(pid)
            except ProcessLookupError:
                pass
            except Exception:
                pass
    return killed

def _keepalive_status():
    active=[]
    for sn,proc in list(_ka_procs.items()):
        if proc.poll() is None: active.append(sn)
    for item in _keepalive_orphans():
        target=item.get("target")
        if target and target not in active:
            active.append(target)
    return active

def audio_select_dlna_renderer(name, location, usn=""):
    if not location.startswith("http://") and not location.startswith("https://"):
        return {"ok":False,"error":"invalid renderer location"}
    lat=_load_audio_latency()
    lat["selected_dlna_renderer"]={"name": name or location, "location": location, "usn": usn}
    _save_audio_latency(lat)
    return {"ok":True,"selected":lat["selected_dlna_renderer"]}

def _pa_dlna_running():
    global _pa_dlna_proc
    if _pa_dlna_proc and _pa_dlna_proc.poll() is None: return True
    try:
        r=subprocess.run(["pgrep","-f",f"pa-dlna.*--port {_PA_DLNA_PORT}"],capture_output=True,text=True,timeout=2)
        return r.returncode==0 and bool(r.stdout.strip())
    except Exception: return False

def _start_pa_dlna():
    global _pa_dlna_proc
    if _pa_dlna_running(): return True
    try:
        log=open(PA_DLNA_LOG,"ab")
        _pa_dlna_proc=subprocess.Popen(["pa-dlna","--nics","eth0","--loglevel","info","--port",_PA_DLNA_PORT],stdout=log,stderr=log)
        return True
    except Exception:
        return False

def _selected_dlna_sink_name():
    lat=_load_audio_latency(); sel=lat.get("selected_dlna_renderer") or {}
    usn=(sel.get("usn") or "").replace("uuid:","").split("::")[0]
    name=(sel.get("name") or "").replace("uuid:","")
    needles=[x for x in (usn, name, name[:12]) if x]
    sinks=_pactl_lines("sinks")
    dlna=[s for s in sinks if _classify_sink(s["name"])=="dlna_output"]
    for s in dlna:
        if any(n and n in s["name"] for n in needles): return s["name"]
    return dlna[0]["name"] if dlna else None

def audio_connect_dlna():
    lat=_load_audio_latency()
    if not lat.get("selected_dlna_renderer"):
        return {"ok":False,"error":"select DLNA renderer first"}
    if not _start_pa_dlna():
        return {"ok":False,"error":"failed to start pa-dlna"}
    sink=None
    for _ in range(20):
        sink=_selected_dlna_sink_name()
        if sink: break
        time.sleep(1)
    if not sink:
        return {"ok":False,"error":"pa-dlna started but no DLNA sink appeared yet", "running": _pa_dlna_running()}
    r=_run(["pactl","set-default-sink",sink], t=5)
    _keepalive_start(sink)
    delay=_apply_dlna_delay()
    return {"ok":r.returncode==0,"sink":sink,"running":_pa_dlna_running(),"keepalive":_keepalive_status(),"delay":delay,"out":(r.stdout+r.stderr).strip()[:200]}

def audio_disconnect_dlna():
    global _pa_dlna_proc
    _keepalive_stop()
    _reset_dlna_delay()
    if _pa_dlna_proc and _pa_dlna_proc.poll() is None:
        _pa_dlna_proc.terminate()
        try: _pa_dlna_proc.wait(timeout=5)
        except Exception: _pa_dlna_proc.kill()
    else:
        subprocess.run(["pkill","-f",f"pa-dlna.*--port {_PA_DLNA_PORT}"],capture_output=True,text=True,timeout=5)
    return {"ok":True,"running":_pa_dlna_running(),"delay_reset":True}

def audio_keepalive(action, sink=None):
    if action=="start" and sink:
        ok=_keepalive_start(sink)
        return {"ok":ok,"active":_keepalive_status(),"orphans":_keepalive_orphans()}
    elif action=="stop" and sink:
        _keepalive_stop(sink)
        return {"ok":True,"active":_keepalive_status(),"orphans":_keepalive_orphans()}
    elif action=="stop_all":
        _keepalive_stop()
        killed=_stop_keepalive_orphans()
        return {"ok":True,"active":_keepalive_status(),"orphans":_keepalive_orphans(),"killed":killed}
    return {"ok":True,"active":_keepalive_status(),"orphans":_keepalive_orphans()}

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

# ── Devices, Wi-Fi, and YouTube diagnostics ───────────────────────────
def _bt_kind(name):
    n=(name or "").lower()
    if "xbox" in n or "wireless controller" in n or "gamepad" in n:
        return "xbox_controller"
    if any(x in n for x in ("soundbar", "speaker", "headphone", "buds", "audio")):
        return "speaker"
    return "unknown"

def _bt_paired_devices():
    out=[]
    r=_run(["bluetoothctl","devices","Paired"], t=5)
    for line in r.stdout.splitlines():
        p=line.split()
        if len(p)>=3 and p[0]=="Device":
            mac=p[1]; name=" ".join(p[2:])
            info=_run(["bluetoothctl","info",mac], t=5).stdout
            connected="Connected: yes" in info
            trusted="Trusted: yes" in info
            paired="Paired: yes" in info or True
            out.append({"mac":mac,"name":name,"kind":_bt_kind(name),"paired":paired,"connected":connected,"trusted":trusted})
    return out

def _bt_scanned_devices():
    r=_run(["bluetoothctl","devices"], t=5)
    out=[]
    known={d["mac"] for d in _bt_paired_devices()}
    for line in r.stdout.splitlines():
        p=line.split()
        if len(p)>=3 and p[0]=="Device":
            mac=p[1]; name=" ".join(p[2:])
            if mac in known: continue
            out.append({"mac":mac,"name":name,"kind":_bt_kind(name),"paired":False,"connected":False,"trusted":False})
    return out

def devices_state():
    audio=audio_state()
    return {"ok":True,"bluetooth":{"paired":_bt_paired_devices()},"audio_devices":audio.get("devices",{}),"default_sink":audio.get("default_sink")}

def bluetooth_scan_devices(seconds=5):
    seconds=max(2,min(12,int(seconds or 5)))
    subprocess.Popen(["bluetoothctl","scan","on"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(seconds)
    _run(["bluetoothctl","scan","off"], t=3)
    return {"ok":True,"devices":_bt_scanned_devices(),"paired":_bt_paired_devices()}

def _wifi_nmcli_available():
    return subprocess.run(["bash","-lc","command -v nmcli >/dev/null"],capture_output=True).returncode==0

def wifi_status():
    if _wifi_nmcli_available():
        r=_run(["nmcli","-t","-f","DEVICE,TYPE,STATE,CONNECTION","device"], t=5)
        devs=[]
        for line in r.stdout.splitlines():
            p=line.split(":")
            if len(p)>=4 and p[1]=="wifi": devs.append({"device":p[0],"state":p[2],"connection":p[3]})
        return {"ok":True,"backend":"nmcli","devices":devs}
    iw=_run(["bash","-lc","iw dev 2>/dev/null | awk '/Interface/{print $2}'"], t=5).stdout.split()
    return {"ok":True,"backend":"iw","devices":[{"device":x,"state":"unknown","connection":""} for x in iw]}

def wifi_scan():
    if _wifi_nmcli_available():
        r=_run(["nmcli","-t","-f","SSID,SIGNAL,SECURITY","device","wifi","list","--rescan","yes"], t=15)
        nets=[]
        for line in r.stdout.splitlines():
            p=line.split(":")
            if not p or not p[0]: continue
            nets.append({"ssid":p[0],"signal":p[1] if len(p)>1 else "", "security":p[2] if len(p)>2 else ""})
        return {"ok":r.returncode==0,"backend":"nmcli","networks":nets,"error":r.stderr.strip()[:200]}
    r=_run(["bash","-lc","iw dev 2>/dev/null | awk '/Interface/{print $2; exit}'"], t=5)
    dev=r.stdout.strip()
    if not dev: return {"ok":False,"backend":"iw","error":"no Wi-Fi interface found"}
    r=_run(["sudo","-n","iw",dev,"scan"], t=15)
    ssids=sorted(set(re.findall(r"SSID: (.+)", r.stdout)))
    return {"ok":r.returncode==0,"backend":"iw","networks":[{"ssid":s,"signal":"","security":""} for s in ssids],"error":r.stderr.strip()[:200]}

def wifi_connect(ssid, password):
    if not ssid: return {"ok":False,"error":"ssid required"}
    if not _wifi_nmcli_available(): return {"ok":False,"error":"Wi-Fi connect requires nmcli on this system"}
    cmd=["nmcli","device","wifi","connect",ssid]
    if password: cmd += ["password", password]
    r=_run(cmd, t=30)
    return {"ok":r.returncode==0,"out":(r.stdout+r.stderr).strip()[:300]}

def youtube_cookie_status():
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),"yt-cookies.txt")
    info={"ok":False,"path":path,"exists":os.path.exists(path),"cookie_count":0,"age_seconds":None,"has_auth_cookies":False,"has_youtube_domain":False}
    if not info["exists"]: return info
    st=os.stat(path); info["age_seconds"]=int(time.time()-st.st_mtime); info["size_bytes"]=st.st_size
    auth_names={"SID","HSID","SSID","APISID","SAPISID","__Secure-1PSID","__Secure-3PSID","LOGIN_INFO"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip() or line.startswith("#"): continue
                info["cookie_count"]+=1
                if "youtube.com" in line or "google.com" in line: info["has_youtube_domain"]=True
                parts=line.rstrip("\n").split("\t")
                if parts and parts[-2] in auth_names: info["has_auth_cookies"]=True
    except Exception as e:
        info["error"]=str(e)
    info["ok"]=info["cookie_count"]>0 and info["has_youtube_domain"]
    info["recommendation"]="OK" if info["ok"] and info["has_auth_cookies"] else "Refresh BrowserOS YouTube cookies from a logged-in browser session."
    return info

def youtube_age_check(url):
    if not url: return {"ok":False,"error":"url required"}
    try:
        surl, meta=resolve(url, DQ)
        return {"ok":True,"title":meta.get("title"),"id":meta.get("id"),"duration":meta.get("dur"),"height":meta.get("h"),"cookies":youtube_cookie_status(),"playable_url":bool(surl)}
    except Exception as e:
        return {"ok":False,"error":str(e)[:400],"cookies":youtube_cookie_status()}

def selftest_testaudio():
    html_doc=page()
    required=[
        'data-t="audio"', 'data-t="devices"', 'id="p-player"', 'id="p-audio"', 'id="p-devices"',
        'id="ta-sinks"', 'id="ta-sources"', 'id="ta-mixer"',
        'id="ta-routes"', 'id="ta-summary"', 'id="ta-raw"', 'id="yt-cookie-status"',
        "sw('player');ytCookieStatus()", "sw('audio');taRefresh()",
    ]
    missing=[x for x in required if x not in html_doc]
    state=audio_state()
    state_keys=["default_sink","default_source","sinks","sources","devices","routes","latency","sink_inputs"]
    missing_state=[x for x in state_keys if x not in state]
    sink_types=[x.get("type") for x in state.get("sinks",[])]
    hdmi_bt_order_ok=True
    if "hdmi" in sink_types and "bt" in sink_types:
        hdmi_bt_order_ok=sink_types.index("hdmi") < sink_types.index("bt")
    ok=not missing and not missing_state and hdmi_bt_order_ok
    return {
        "ok": ok,
        "missing_markup": missing,
        "missing_state": missing_state,
        "sink_types": sink_types,
        "source_types": [x.get("type") for x in state.get("sources",[])],
        "hdmi_before_bt": hdmi_bt_order_ok,
        "layout": "outputs-left-inputs-right-preserved",
        "keepalive": state.get("keepalive",[]),
        "dlna_connected": state.get("dlna_connected",False),
    }

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
#topbar{display:flex;justify-content:space-between;align-items:center;gap:.5rem;margin-bottom:.15rem}
#lang-switch{display:flex;gap:.25rem;align-items:center}
.lang-btn{font-size:.78rem;padding:.22rem .42rem;border-radius:999px;line-height:1;border:1px solid #30363d;background:#161b22;color:#c9d1d9}
.lang-btn.active{background:#1a5276;border-color:#58a6ff;color:#fff}
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
function mute(){api('/mpv/toggle').then(r=>msg(r.paused!==undefined?(r.paused?'Muted':'Unmuted'):'?','info'));setTimeout(st,300)}
let seeking=false,lastPos=0,lastDur=0;
function seekTo(v){if(lastDur>0){let pos=(v/100)*lastDur;api('/mpv/seekabs?pos='+pos.toFixed(1))}}
async function st(){let r=await api('/mpv/status'),s=$('#st');if(!r.on){s.textContent=r.err?'Error':'—';return}let p=fmt(r.pos),du=fmt(r.dur);s.innerHTML='<b>'+esc(r.title||'?')+'</b><br>'+p+'/'+du+(r.paused?' ⏸':'')+' Vol:'+Math.round(r.vol)+'% '+r.q;lastPos=r.pos||0;lastDur=r.dur||0;if(!seeking&&lastDur>0){let pct=(lastPos/lastDur)*100;$('#sbar').value=pct;$('#stime').textContent=fmt(lastPos);$('#dtime').textContent=fmt(lastDur)}}
function fmt(s){if(!s)return'0:00';let m=Math.floor(s/60),sc=Math.floor(s%60);return m+':'+(sc<10?'0':'')+sc}
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#39;')}
function jsarg(s){return String(s??'').replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/\n/g,'\\n').replace(/\r/g,'\\r').replace(/</g,'\\x3C').replace(/>/g,'\\x3E').replace(/&/g,'\\x26')}
const LANG_KEY='rpidash-lang'
const I18N={cz:{player:'Přehrávač',apps:'Aplikace',cec:'CEC',kodi:'Kodi',audio:'Audio',devices:'Zařízení',terminal:'Terminál',status:'Stav',quick:'Rychlé',ageCookies:'Věk / cookies',cookieStatus:'Stav cookies',ageCheck:'Kontrola věku',play:'Přehrát',refresh:'Obnovit',connect:'Připojit',disconnect:'Odpojit',saveApply:'Uložit + použít',inputUrl:'YouTube nebo přímá URL...',audioDelay:'Audio delay (ms):',playerDesc:'Přehrávání YouTube/mpv a diagnostika cookies.',appsDesc:'Spuštění aplikací a návrat do dashboardu.',cecPower:'Napájení',cecBridge:'Remote→MPV Bridge',cecNav:'Navigace',cecVol:'Hlasitost',cecInput:'Vstup',cecDevices:'Zařízení',kodiTitle:'Kodi JSON-RPC launcher',kodiDesc:'Legacy cesta pro odeslání URL do lokálního Kodi na 127.0.0.1:9090 přes Player.Open. Smysl má jen pokud Kodi skutečně běží jako renderer/přehrávač; běžné YouTube/mpv přehrávání používá kartu Player.',audioTitle:'Audio & Media',audioDesc:'Hlavní směrování zvuku a mixer. Párování reproduktorů je v Zařízeních; směrování výstupu je zde.',outputSinks:'Výstupní zařízení',inputSources:'Vstupní zdroje',mixer:'Mixér — aktivní streamy',audioRouting:'Směrování zvuku',dlnaLatency:'Kompenzace DLNA zpoždění',ytAge:'YouTube věk / cookies',ytAgeDesc:'Kontrola čerstvosti cookies bez vyzrazení hodnot. Použij, když age-restricted video nejde přehrát.',diagnostics:'Diagnostika',devicesTitle:'Zařízení',devicesDesc:'Páruj a připojuj hardware zde. Směrování reproduktoru a hlasitost zůstávají v Audio.',btPair:'Párování Bluetooth',wifiConfig:'Wi‑Fi konfigurace',roles:'Doporučené role zařízení',rolesDesc:'• Reproduktory/sluchátka/soundbary: páruj/připoj/důvěřuj zde, pak zvol routování v Audio.<br>• Xbox ovladače/gamepady: páruj/připoj/důvěřuj zde pro vstupní použití; žádné audio routování se neprovádí.<br>• Remote mikrofon a USB Alexa input jsou zobrazeny v Audio jako zdroje.<br>• Budoucí doplnění: HDMI-CEC inventář, Tailscale stav, health USB/storage zařízení.',termConnect:'Připojit',termDisconnect:'Odpojit',scan:'Skenovat',pair:'Párovat',trust:'Důvěřovat',remove:'Odebrat',found:'Nalezeno',paired:'spárováno',connected:'Připojeno',disconnected:'Odpojeno',playing:'Přehrávám',paused:'Pozastaveno',stopped:'Zastaveno',language:'Jazyk',clickScan:'Klikni na Skenovat',clickScanRefresh:'Klikni na Skenovat nebo Obnovit',clickCookieStatus:'Klikni na Stav cookies' ,appsLaunch:'Spustit aplikaci',appsReturn:'Návrat do Dashboardu',appsReturnDesc:'• <b>Ctrl+C</b> — ukončí většinu aplikací<br>• <b>Ctrl+Q</b> — ukončí Steam Link<br>• <b>tlačítko ZASTAVIT</b> — vynutí návrat<br>• Aplikace běží přímo na TV, dashboard se automaticky vrátí po ukončení',cecBridgeDesc:'Play/Pause, Stop, Seek, Vol via TV remote',ssid:'SSID',password:'Password' },en:{player:'Player',apps:'Apps',cec:'CEC',kodi:'Kodi',audio:'Audio',devices:'Devices',terminal:'Terminal',status:'Status',quick:'Quick',ageCookies:'Age / cookies',cookieStatus:'Cookie status',ageCheck:'Age check',play:'Play',refresh:'Refresh',connect:'Connect',disconnect:'Disconnect',saveApply:'Save + apply',inputUrl:'YouTube or direct URL...',audioDelay:'Audio delay (ms):',playerDesc:'YouTube/mpv playback and cookie diagnostics.',appsDesc:'Launch apps and return to the dashboard.',cecPower:'Power',cecBridge:'Remote→MPV Bridge',cecNav:'Navigation',cecVol:'Volume',cecInput:'Input',cecDevices:'Devices',kodiTitle:'Kodi JSON-RPC launcher',kodiDesc:'Legacy route for sending a URL to a local Kodi instance on 127.0.0.1:9090 via Player.Open. It is useful only if Kodi is installed/running as a renderer; normal YouTube/mpv playback uses the Player tab.',audioTitle:'Audio & Media',audioDesc:'Primary audio routing and mixer. Speaker pairing lives in Devices; output routing lives here.',outputSinks:'Output Sinks',inputSources:'Input Sources',mixer:'Mixer — Active Streams',audioRouting:'Audio Routing',dlnaLatency:'DLNA Latency Compensation',ytAge:'YouTube Age / Cookies',ytAgeDesc:'Checks cookie freshness without exposing cookie values. Use this when age-restricted videos fail.',diagnostics:'Diagnostics',devicesTitle:'Devices',devicesDesc:'Pair and connect hardware here. Speaker output routing and volume remain in Audio.',btPair:'Bluetooth Pairing',wifiConfig:'Wi‑Fi Configuration',roles:'Suggested Device Roles',rolesDesc:'• Speakers/headphones/soundbars: pair/connect/trust here, then choose routing in Audio.<br>• Xbox controllers/gamepads: pair/connect/trust here for input use; no audio routing is applied.<br>• Remote microphone and USB Alexa input are shown in Audio as sources.<br>• Future additions: HDMI-CEC device inventory, Tailscale status, storage/USB device health.',termConnect:'Connect',termDisconnect:'Disconnect',scan:'Scan',pair:'Pair',trust:'Trust',remove:'Remove',found:'Found',paired:'paired',connected:'Connected',disconnected:'Disconnected',playing:'Playing',paused:'Paused',stopped:'Stopped',language:'Language',clickScan:'Click Scan',clickScanRefresh:'Click Scan or Refresh',clickCookieStatus:'Click Cookie status' ,appsLaunch:'Launch app',appsReturn:'Back to Dashboard',appsReturnDesc:'• <b>Ctrl+C</b> — closes most applications<br>• <b>Ctrl+Q</b> — closes Steam Link<br>• <b>STOP button</b> — forces a return<br>• Apps run directly on the TV and the dashboard returns automatically after exit',cecBridgeDesc:'Play/Pause, Stop, Seek, Volume via TV remote',ssid:'SSID',password:'Password' }}
let LANG=(localStorage.getItem(LANG_KEY)||'cz').toLowerCase()==='en'?'en':'cz'
function L(k){return (I18N[LANG]&&I18N[LANG][k])||((I18N.cz&&I18N.cz[k])||k)}
function setLang(code){LANG=(code||'cz').toLowerCase()==='en'?'en':'cz';try{localStorage.setItem(LANG_KEY,LANG)}catch{};applyLang()}
function applyLang(){document.documentElement.lang=LANG==='en'?'en':'cs';document.querySelectorAll('[data-i18n]').forEach(el=>{let key=el.dataset.i18n;let txt=L(key);if(el.dataset.i18nAttr==='placeholder'){el.placeholder=txt;return}if(el.dataset.i18nAttr==='title'){el.title=txt;return}let icon=el.dataset.icon||'';el.innerHTML=(icon?icon+' ':'')+txt});document.querySelectorAll('[data-lang-btn]').forEach(btn=>btn.classList.toggle('active',btn.dataset.langBtn===LANG));let ls=$('#lang-status');if(ls)ls.textContent=LANG==='en'?'EN':'CZ'}
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
async function refreshDeviceViews(){try{devicesRefresh()}catch(e){}try{devs()}catch(e){}}
async function btPair(mac){msg('Pairing '+mac+'...','info');let r=await api('/bt/pair?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(refreshDeviceViews,2000)}
async function btConnect(mac){msg('Connecting '+mac+'...','info');let r=await api('/bt/connect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(refreshDeviceViews,2000)}
async function btDisconnect(mac){msg('Disconnecting '+mac+'...','info');let r=await api('/bt/disconnect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(refreshDeviceViews,2000)}
async function btRemove(mac){msg('Removing '+mac+'...','info');let r=await api('/bt/remove?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(refreshDeviceViews,2000)}
async function btTrust(mac){msg('Trusting '+mac+'...','info');let r=await api('/bt/trust?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(refreshDeviceViews,2000)}
async function dlnaScan(){msg('Scanning DLNA...','info');let r=await api('/dlna/scan');if(r.devices){let h=r.devices.map(d=>`<div>${d.usn.split('::')[0]} → ${d.location}</div>`).join('');$('#dlna-list').innerHTML=h;$('#dlna-status').textContent=r.count+' renderers';msg('Found '+r.count+' DLNA renderers','ok')}else{msg(r.error||'Scan failed','err')}}
function badge(on,label){return '<span class="badge '+(on?'ok':'err')+'">'+label+'</span>'}
let taVolTimers={};
function taSetVolDebounced(kind,name,v){let key=kind+':'+name;clearTimeout(taVolTimers[key]);taVolTimers[key]=setTimeout(()=>taSetVol(kind,name,v),250)}
function meter(v,kind,name){let n=(v==null?0:v);if(!kind||!name)return '<div class="meter"><span style="width:'+n+'%"></span></div><div class="media-meta">Volume: '+(v==null?'—':v+'%')+'</div>';let id='vol-'+kind+'-'+esc(name).replace(/[^a-zA-Z0-9]/g,'_').substring(0,30);return '<div style="display:flex;align-items:center;gap:.4rem;margin:.2rem 0"><input type="range" id="'+id+'" min="0" max="150" value="'+n+'" step="1" style="flex:1;height:6px;accent-color:#58a6ff;cursor:pointer" oninput="taSetVolDebounced(\''+kind+'\',\''+jsarg(name)+'\',this.value)" onchange="taSetVol(\''+kind+'\',\''+jsarg(name)+'\',this.value)" ontouchstart="event.stopPropagation()"><span style="min-width:36px;font-size:.8em;text-align:right">'+(v==null?'—':v+'%')+'</span><button onclick="taMute(\''+kind+'\',\''+jsarg(name)+'\')" style="font-size:.75em;padding:2px 6px" title="Mute/unmute">🔇</button></div>'}
function shortName(n){let s=(n||'').replace('alsa_output.platform-3f902000.hdmi.hdmi-stereo','HDMI').replace('alsa_output.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-stereo','USB audio output').replace('alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback','Alexa USB input').replace('alsa_input.usb-XING_WEI_2.4G_USB_USB_Composite_Device-00.mono-fallback','Remote microphone');if(s.startsWith('bluez_output.'))s='BT Soundbar';if(s.includes('WiiMu')||s.includes('LinkPlayer'))s='DLNA Output';if(s.includes('LG TV'))s='DLNA LG TV';return s}
function deviceCard(icon,title,d,isDefault){let ok=d&&d.present;let defBadge=isDefault?' <span class="badge ok" style="font-size:.6em">CONNECTED</span>':'';let kind=String((d&&d.type)||'').includes('input')?'source':'sink';return '<div class="media-card"><h4>'+icon+' '+title+' '+badge(ok,ok?'ONLINE':'MISSING')+defBadge+'</h4>'+meter(d&&d.volume,kind,d.name)+'<div class="media-meta">'+esc(shortName((d&&d.name)||'not detected'))+'<br>State: '+esc((d&&d.state)||'—')+'</div></div>'}
function btSoundbarCard(d,isDefault){let ok=d&&d.present,paired=d&&d.paired;let defBadge=isDefault?' <span class="badge ok" style="font-size:.6em">CONNECTED</span>':'';let h='<div class="media-card"><h4>🎧 BT Soundbar '+badge(ok,ok?'ONLINE':(paired?'PAIRED':'MISSING'))+defBadge+'</h4>'+meter(d&&d.volume,'sink',d.name);h+='<div class="media-meta">'+esc((d&&d.label)||'Samsung Soundbar')+'<br>MAC: '+esc((d&&d.mac)||'—')+'<br>Status: '+esc(ok?'Connected':'Paired, not connected')+'</div>';if(paired&&!ok)h+='<div class="row" style="margin-top:.45rem"><button onclick="taBtConnect(\''+jsarg(d.mac)+'\')">🔌 Connect Soundbar</button></div>';return h+'</div>'}
function dlnaOutputCard(d,selected,connected,keepalive){let ok=d&&d.present;let target=selected?('<br>Selected target: '+esc(selected.name||selected.location)):'<br>No target selected yet.';let connectBtns='';if(selected){if(connected){connectBtns='<button onclick="taDlnaDisconnect()" class="danger" style="font-size:.8em">⏹ Disconnect</button>'}else{connectBtns='<button onclick="taDlnaConnect()" style="font-size:.8em">🔌 Connect</button>'}}let kaBadge='';let hasDlnaKeepalive=keepalive&&d&&d.name&&keepalive.some(k=>k===d.name);if(hasDlnaKeepalive){kaBadge='<span class="badge ok" style="font-size:.65em;margin-left:.3rem">KEEPALIVE</span>'}let status=connected?badge(true,'CONNECTED'):(ok?badge(ok,'NOT CONNECTED'):badge(false,'NOT CONNECTED'));let h='<div class="media-card"><h4>📡 DLNA Output '+status+kaBadge+'</h4>'+meter(d&&d.volume,'sink',d.name)+'<div class="media-meta">Send RPi sound to a network DLNA speaker/TV.'+target+'</div><div class="row" style="margin-top:.4rem;gap:.4rem"><button onclick="taDlnaScan()">🔍 Scan renderers</button>'+connectBtns+'</div><div id="ta-dlna-out-list" class="media-meta" style="margin-top:.35rem">—</div></div>';return h}
function taHumanSummary(r){let d=r.devices||{},lat=r.latency||{},inputs=r.sink_inputs||[];let lines=[];lines.push('Default output: '+shortName(r.default_sink||'—'));lines.push('HDMI: '+(d.hdmi&&d.hdmi.present?'online, volume '+d.hdmi.volume+'%':'not available'));let ka=r.keepalive||[];lines.push('BT Soundbar: '+(d.bt_soundbar&&d.bt_soundbar.present?(ka.some(k=>k.startsWith('bluez'))?'connected + keepalive':'connected'):'paired but not connected'));lines.push('DLNA Output: '+((r.dlna_connected)?'connected + keepalive':((d.dlna_output&&d.dlna_output.present)?'active, not connected':'not connected')));if(lat.selected_dlna_renderer)lines.push('Selected DLNA target: '+(lat.selected_dlna_renderer.name||lat.selected_dlna_renderer.location));lines.push('Active streams: '+(inputs.length?inputs.map(i=>'playing through '+i.sink).join(', '):'none'));let dl=r.dlna_connected;let dly=lat.dlna_output_offset_ms||0;lines.push('DLNA delay offset: '+dly+' ms'+(dl&&dly?' (active, mpv audio-delay set)':''));return lines.map(x=>'<div>• '+esc(x)+'</div>').join('')}
async function taRefresh(){let r=await api('/audio/state');if(r.error){msg(r.error,'err');return}let d=r.devices||{};let sources=r.sources||[];let inputs=r.sink_inputs||[];let lat=r.latency||{};let outHtml='';let ds=r.default_sink||'';if(d.hdmi&&d.hdmi.present)outHtml+=deviceCard('📺','HDMI',d.hdmi,ds.includes('hdmi'));outHtml+=btSoundbarCard(d.bt_soundbar||{},ds.includes('bluez'));outHtml+=dlnaOutputCard(d.dlna_output||{},lat.selected_dlna_renderer,r.dlna_connected,r.keepalive);if(d.usb_output&&d.usb_output.present)outHtml+=deviceCard('🔌','USB Output',d.usb_output,ds.includes('usb'));$('#ta-sinks').innerHTML=outHtml;let srcHtml='';sources.forEach(s=>{let icon=s.type==='usb_input'?'🎙️':(s.type==='remote_input'?'🎮':(s.type==='dlna_input'?'📡':'🔊'));let title=s.type==='usb_input'?'Alexa USB Input':(s.type==='remote_input'?'Remote Mic':(s.type==='dlna_input'?'DLNA Input':'Other'));srcHtml+=deviceCard(icon,title,s)});srcHtml+='<div class="media-card"><h4>📡 DLNA Input '+badge(false,'PLANNED')+'</h4><div class="media-meta">Receive audio from another PC/device on the network. Requires renderer configuration.</div></div>';$('#ta-sources').innerHTML=srcHtml;let mixerHtml='';let ka=r.keepalive||[];let realInputs=inputs.filter(i=>{if(!ka.length)return true;return!ka.some(k=>i.sink===k)});if(realInputs.length){realInputs.forEach(i=>{let sn=shortName(i.sink);mixerHtml+='<div class="media-card route-card"><h4>🎵 Playing through '+esc(sn)+'</h4><div class="media-meta">Audio is currently routed to '+esc(sn)+'. Format: '+esc(i.format||'—')+'</div></div>'});}else if(inputs.length){mixerHtml='<div class="media-card"><h4>🎵 Active Streams</h4><div class="media-meta">Audio playing (keepalive streams hidden).</div></div>'}else{mixerHtml='<div class="media-card"><h4>🎵 Active Streams</h4><div class="media-meta">No active audio streams.</div></div>'}$('#ta-mixer').innerHTML=mixerHtml;let route=r.routes&&r.routes.alexa_to_bt;let ready=route&&route.ready;let warn=ready?'Ready.':'Needs online BT Soundbar and USB Alexa input before Start.';let startDisabled=ready?'':' disabled title="BT Soundbar or USB input missing"';$('#ta-routes').innerHTML='<div class="media-card route-card '+(route&&route.on?'on':'off')+'"><h4>🔁 Alexa AUX → BT Soundbar '+badge(route&&route.on,route&&route.on?'ON':(ready?'READY':'NOT READY'))+'</h4><div class="media-meta">USB C-Media mono input → PipeWire loopback → Samsung Soundbar A2DP<br>'+warn+'</div><div class="row" style="margin-top:.45rem"><button onclick="taRoute(\'start\')"'+startDisabled+'>▶ Start</button><button onclick="taRoute(\'stop\')" class="danger">⏹ Stop</button></div><div class="media-meta">Module: '+esc((route&&route.module_id)||'—')+'</div></div>';$('#ta-default').textContent=shortName(r.default_sink||'—');$('#ta-lat-dlna-offset').value=lat.dlna_output_offset_ms||0;$('#ta-summary').innerHTML=taHumanSummary(r);$('#ta-raw').textContent=JSON.stringify(r,null,2)}
async function taRoute(a){let r=await api('/audio/route/alexa-bt?action='+a);msg(r.ok?'Route '+a+' OK':(r.error||r.out||'Route failed'),r.ok?'ok':'err');setTimeout(taRefresh,800)}
async function taBtConnect(mac){msg('Connecting Soundbar...','info');let r=await api('/bt/connect?mac='+encodeURIComponent(mac));msg(r.result||r.error,r.result?'ok':'err');setTimeout(taRefresh,1500)}
async function taSwitch(t){let r=await api('/audio/'+t);msg(r.result||r.err,r.result?'ok':'err');setTimeout(taRefresh,800)}
async function taSetVol(kind,name,v){let r=await api('/audio/volume?kind='+kind+'&name='+encodeURIComponent(name)+'&volume='+v);msg(r.ok?'Volume → '+v+'%':(r.error||'fail'),r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taMute(kind,name){let r=await api('/audio/mute?kind='+kind+'&name='+encodeURIComponent(name));msg(r.ok?'Mute toggled':(r.error||'fail'),r.ok?'ok':'err')}
async function taSetDefault(name){let r=await api('/audio/default-sink?name='+encodeURIComponent(name));msg(r.ok?'Default → '+name.split('.').pop():r.error||'fail',r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taSetLatency(key,v){let r=await api('/audio/latency?key='+key+'&value='+v);msg(r.ok?'Latency saved':r.error||'fail',r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taDlnaSelect(name,location,usn){let r=await api('/dlna/select?name='+encodeURIComponent(name)+'&location='+encodeURIComponent(location)+'&usn='+encodeURIComponent(usn||''));msg(r.ok?'DLNA target selected':(r.error||'select failed'),r.ok?'ok':'err');setTimeout(taRefresh,600)}
async function taDlnaConnect(){msg('Connecting DLNA renderer...','info');let r=await api('/dlna/connect');msg(r.ok?'Connected to DLNA':(r.error||'connect failed'),r.ok?'ok':'err');setTimeout(taRefresh,3000)}
async function taDlnaDisconnect(){msg('Disconnecting DLNA...','info');let r=await api('/dlna/disconnect');msg(r.ok?'DLNA disconnected':(r.error||'failed'),r.ok?'ok':'err');setTimeout(taRefresh,1000)}
async function taKeepalive(action,sink){let r=await api('/keepalive?action='+action+(sink?'&sink='+encodeURIComponent(sink):''));return r}
async function taDlnaScan(){msg('Scanning DLNA renderers...','info');let r=await api('/dlna/scan');if(r.devices&&r.devices.length){let h='<div style="margin-top:.3rem">';r.devices.forEach(d=>{h+='<div style="margin:3px 0;display:flex;gap:6px;align-items:center;border:1px solid #30363d;border-radius:.3rem;padding:.3rem .5rem;flex-wrap:wrap">📡 <b>'+esc(d.name)+'</b> <span style="color:#8b949e;font-size:.7em">'+esc(d.location||'')+'</span><button onclick="taDlnaSelect(\''+jsarg(d.name||'DLNA renderer')+'\',\''+jsarg(d.location||'')+'\',\''+jsarg(d.usn||'')+'\')" style="font-size:.7em;padding:2px 8px">Select</button></div>'});h+='</div>';let el=$('#ta-dlna-out-list');if(el)el.innerHTML=h;msg('Found '+r.count+' DLNA renderers','ok')}else{let el=$('#ta-dlna-out-list');if(el)el.innerHTML='<div style="color:#8b949e">No renderers found</div>';msg(r.error||'No DLNA renderers found','err')}}
function devIcon(k){return k==='xbox_controller'?'🎮':(k==='speaker'?'🔊':'📡')}
function renderBtDevices(devs){if(!devs||!devs.length)return '<div>No Bluetooth devices listed.</div>';return devs.map(d=>'<div class="media-card" style="min-height:70px;margin:.3rem 0"><h4>'+devIcon(d.kind)+' '+esc(d.name||'Unknown')+' '+badge(!!d.connected,d.connected?'CONNECTED':(d.paired?'PAIRED':'FOUND'))+'</h4><div class="media-meta">MAC: '+esc(d.mac)+'<br>Role: '+esc(d.kind||'unknown')+' · Trusted: '+(d.trusted?'yes':'no')+'</div><div class="row" style="margin-top:.35rem"><button data-i18n="pair" onclick="btPair(\''+jsarg(d.mac)+'\')">Pair</button><button data-i18n="connect" onclick="btConnect(\''+jsarg(d.mac)+'\')">Connect</button><button data-i18n="trust" onclick="btTrust(\''+jsarg(d.mac)+'\')">Trust</button><button class="danger" data-i18n="remove" onclick="btRemove(\''+jsarg(d.mac)+'\')">Remove</button></div></div>').join('')}
async function devicesRefresh(){let r=await api('/devices/state');if(r.error){msg(r.error,'err');return}$('#dev-bt-list').innerHTML=renderBtDevices((r.bluetooth&&r.bluetooth.paired)||[]);$('#dev-bt-status').textContent=((r.bluetooth&&r.bluetooth.paired)||[]).length+' paired'}
async function deviceBtScan(){msg(L('scan')+' Bluetooth...','info');let r=await api('/devices/bt/scan?seconds=6');let all=[...(r.paired||[]),...(r.devices||[])];$('#dev-bt-list').innerHTML=renderBtDevices(all);$('#dev-bt-status').textContent=(r.devices||[]).length+' '+L('found')+', '+(r.paired||[]).length+' '+L('paired');msg(L('scan')+' Bluetooth done','ok')}
async function wifiStatus(){let r=await api('/wifi/status');$('#wifi-list').innerHTML='<pre>'+esc(JSON.stringify(r,null,2))+'</pre>'}
async function wifiScan(){msg('Scanning Wi-Fi...','info');let r=await api('/wifi/scan');if(r.networks){let h=r.networks.map(n=>'<div style="margin:3px 0"><button onclick="$(\'#wifi-ssid\').value=\''+jsarg(n.ssid)+'\'" style="font-size:.72em;padding:2px 8px">Use</button> '+esc(n.ssid)+' <span style="color:#8b949e">'+esc(n.signal||'')+' '+esc(n.security||'')+'</span></div>').join('');$('#wifi-list').innerHTML=h||'No networks found';msg('Wi-Fi scan done','ok')}else{$('#wifi-list').innerHTML='<pre>'+esc(JSON.stringify(r,null,2))+'</pre>';msg(r.error||'Wi-Fi scan failed','err')}}
async function wifiConnect(){let ssid=$('#wifi-ssid').value.trim(),pw=$('#wifi-pass').value;if(!ssid){msg('SSID required','err');return}let r=await api('/wifi/connect?ssid='+encodeURIComponent(ssid)+'&password='+encodeURIComponent(pw));msg(r.ok?'Wi-Fi connected':(r.error||r.out||'Wi-Fi failed'),r.ok?'ok':'err');wifiStatus()}
async function ytCookieStatus(){let r=await api('/youtube/cookies/status');$('#yt-cookie-status').textContent=JSON.stringify(r,null,2)}
async function ytAgeCheck(){let u=$('#yt-age-url').value.trim();if(!u){msg('Enter YouTube URL','err');return}msg('Checking YouTube age/cookies...','info');let r=await api('/youtube/age-check?url='+encodeURIComponent(u));$('#yt-cookie-status').textContent=JSON.stringify(r,null,2);msg(r.ok?'Video is extractable':'Age/cookie check failed',r.ok?'ok':'err')}
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
setInterval(()=>{st();updBr()},3000);kStat();ytCookieStatus();applyLang();
"""

QO="\n".join(f'<option value="{k}"{" selected" if k==DQ else ""}>{k}</option>' for k in QUALITY)

def page():
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RPi-TV</title><style>{CSS}</style></head><body>
<div id="topbar"><h1 id="app-title">RPi-TV</h1><div id="lang-switch"><button class="lang-btn" data-lang-btn="en" onclick="setLang('en')" title="English" aria-label="English">🇬🇧</button><button class="lang-btn" data-lang-btn="cz" onclick="setLang('cz')" title="Čeština" aria-label="Čeština">🇨🇿</button></div></div><div id="toast"></div>
<div class="tabs">
<button id="tab-player" class="tab active" data-t="player" data-i18n="player" data-icon="🎬" onclick="sw('player');ytCookieStatus()">🎬 Player</button>
<button id="tab-apps" class="tab" data-t="apps" data-i18n="apps" data-icon="🚀" onclick="sw('apps')">🚀 Apps</button>
<button id="tab-cec" class="tab" data-t="cec" data-i18n="cec" data-icon="📺" onclick="sw('cec')">📺 CEC</button>
<button id="tab-kodi" class="tab" data-t="kodi" data-i18n="kodi" data-icon="📦" onclick="sw('kodi')">📦 Kodi</button>
<button id="tab-audio" class="tab" data-t="audio" data-i18n="audio" data-icon="🔊" onclick="sw('audio');taRefresh()">🔊 Audio</button>
<button id="tab-devices" class="tab" data-t="devices" data-i18n="devices" data-icon="🧩" onclick="sw('devices');devicesRefresh();wifiStatus()">🧩 Devices</button>
<button id="tab-terminal" class="tab" data-t="terminal" data-i18n="terminal" data-icon="💻" onclick="sw('terminal')">💻 Terminal</button></div>
<div id="p-player" class="pnl active"><div class="sec">
<div class="row"><input id="url" data-i18n="inputUrl" data-i18n-attr="placeholder" placeholder="YouTube or direct URL..." style="flex:1"><select id="qual">{QO}</select></div>
<div class="row" style="margin-top:.3rem">
<button data-i18n="play" data-icon="▶" onclick="play()">▶ Play</button><button onclick="pause()">⏸</button><button onclick="stop()" class="danger">⏹</button>
<button onclick="seek(-10)">⏪10</button><button onclick="seek(10)">10⏩</button>
<button onclick="vol(-10)">🔉</button><button onclick="vol(10)">🔊</button><button onclick="mute()" style="font-size:.85rem">🔇</button></div>
<div style="margin-top:.4rem"><div style="display:flex;align-items:center;gap:.4rem"><span id="stime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span><input type="range" id="sbar" min="0" max="100" value="0" step="0.1" style="flex:1;height:6px;accent-color:#58a6ff;cursor:pointer" oninput="seekTo(this.value)" ontouchstart="seeking=true" ontouchend="seeking=false"><span id="dtime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span></div></div></div>
<div class="sec"><h3 data-i18n="status">Status</h3><div id="st">—</div></div>
<div class="sec"><h3 data-i18n="quick">Quick</h3><div class="row">
<button onclick="qu('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" style="font-size:.75rem">🎵 Rick Astley</button>
<button onclick="qu('https://www.youtube.com/watch?v=9bZkp7q19f0')" style="font-size:.75rem">🎵 Gangnam</button></div></div>
<div class="sec"><h3 data-i18n="ytAge">YouTube Age / Cookies</h3><div class="media-meta" data-i18n="ytAgeDesc">Checks cookie freshness without exposing cookie values. Use this when age-restricted videos fail.</div><div class="row" style="margin-top:.35rem"><input id="yt-age-url" data-i18n="inputUrl" data-i18n-attr="placeholder" placeholder="YouTube URL for age-check..." style="flex:1"><button data-icon="🍪" data-i18n="cookieStatus" onclick="ytCookieStatus()">🍪 Cookie status</button><button data-icon="🔞" data-i18n="ageCheck" onclick="ytAgeCheck()">🔞 Age check</button></div><pre id="yt-cookie-status" data-i18n="clickCookieStatus">Click Cookie status</pre></div></div>
</div>
<div id="p-apps" class="pnl"><div class="sec"><h3 data-i18n="appsLaunch">Spustit aplikaci</h3>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:.5rem">
<button onclick="launchApp('steamlink')" style="padding:12px;font-size:1rem">🎮 Steam Link</button>
<button onclick="launchApp('gfn')" style="padding:12px;font-size:1rem">🎯 GeForce Now</button>
<button onclick="launchApp('mpv')" style="padding:12px;font-size:1rem">🎬 MPV Přehrávač</button>
<button onclick="launchApp('spotify')" style="padding:12px;font-size:1rem">🎵 Spotify</button>
<button onclick="launchApp('amazon')" style="padding:12px;font-size:1rem">🎶 Amazon Music</button>
<button onclick="stopApp()" style="padding:12px;font-size:1rem;color:#f85149;border:2px solid #f85149">⏹ ZASTAVIT & VRÁTIT SE</button>
</div></div>
<div class="sec"><h3 data-i18n="appsReturn">Návrat do Dashboardu</h3>
<div style="font-size:.85em;color:#c9d1d9" data-i18n="appsReturnDesc">
• <b>Ctrl+C</b> — ukončí většinu aplikací<br>
• <b>Ctrl+Q</b> — ukončí Steam Link<br>
• <b>tlačítko ZASTAVIT</b> — vynutí návrat<br>
• Aplikace běží přímo na TV, dashboard se automaticky vrátí po ukončení
</div></div></div>
<div id="p-cec" class="pnl"><div class="sec"><h3 data-i18n="cecPower">Power</h3><div class="row">
<button onclick="cec('on 0')">🟢 On</button><button onclick="cec('standby 0')" class="danger">🔴 Off</button>
<button onclick="cecScan()">🔍 Scan</button></div></div>
<div class="sec"><h3 data-i18n="cecBridge">Remote→MPV Bridge</h3><div class="row">
<button id="brb" onclick="cecBr()">▶ Start</button><span id="brs" style="font-size:.75em;color:#8b949e">OFF</span></div>
<div style="font-size:.7em;color:#666" data-i18n="cecBridgeDesc">Play/Pause, Stop, Seek, Vol via TV remote</div></div>
<div class="sec"><h3 data-i18n="cecNav">Nav</h3><div class="cec-grid">
<button onclick="cecKey('menu')">📋</button><button onclick="cecKey('up')">▲</button><button onclick="cecKey('channels+')">CH+</button>
<button onclick="cecKey('left')">◀</button><button onclick="cecKey('select')" style="font-size:.7rem">OK</button><button onclick="cecKey('right')">▶</button>
<button onclick="cecKey('back')">◀◀</button><button onclick="cecKey('down')">▼</button><button onclick="cecKey('channels-')">CH-</button></div></div>
<div class="sec"><h3 data-i18n="cecVol">Vol</h3><div class="vol-row">
<button onclick="cec('voldown')">🔉−</button><button onclick="cec('mute')">🔇</button><button onclick="cec('volup')">🔊+</button></div></div>
<div class="sec"><h3 data-i18n="cecInput">Input</h3><div class="row">
<button onclick="cecIn(1)">HDMI1</button><button onclick="cecIn(2)">HDMI2</button><button onclick="cecIn(3)">HDMI3</button></div></div>
<div class="sec"><h3 data-i18n="cecDevices">Devices</h3><div id="cdev" data-i18n="clickScan" style="font-size:.8em;color:#8b949e">Click Scan</div></div></div>
<div id="p-kodi" class="pnl"><div class="sec"><h3 data-i18n="kodiTitle">Kodi JSON-RPC launcher</h3>
<div class="media-meta" data-i18n="kodiDesc">Legacy route for sending a URL to a local Kodi instance on 127.0.0.1:9090 via Player.Open. It is useful only if Kodi is installed/running as a renderer; normal YouTube/mpv playback uses the Player tab.</div>
<div class="row" style="margin-top:.35rem"><input id="kurl" data-i18n="inputUrl" data-i18n-attr="placeholder" placeholder="URL for Kodi..." style="flex:1"><button onclick="kPlay()">▶ Kodi</button></div>
<div id="kst" style="font-size:.8em;color:#8b949e;margin-top:.2rem">—</div></div></div>
<div id="p-audio" class="pnl">
<div class="sec"><div class="media-head"><div><h3 data-i18n="audioTitle">Audio & Media</h3><div class="media-meta" data-i18n="audioDesc">Primary audio routing and mixer. Speaker pairing lives in Devices; output routing lives here.</div></div><div class="row"><button onclick="taSwitch('bt')">🎧 BT</button><button onclick="taSwitch('hdmi')">📺 HDMI</button><button onclick="taSwitch('dlna')">📡 DLNA</button><button data-i18n="refresh" data-icon="🔄" onclick="taRefresh()">🔄 Refresh</button></div></div><div class="media-meta">Default sink: <span id="ta-default">—</span></div></div>
<div class="media-grid"><div><div class="sec"><h3 data-i18n="outputSinks">Output Sinks</h3><div id="ta-sinks" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div><div><div class="sec"><h3 data-i18n="inputSources">Input Sources</h3><div id="ta-sources" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div></div>
<div class="sec"><h3 data-i18n="mixer">Mixer — Active Streams</h3><div id="ta-mixer" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3 data-i18n="audioRouting">Audio Routing</h3><div id="ta-routes" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3 data-i18n="dlnaLatency">DLNA Latency Compensation</h3><div style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">
<label style="font-size:.72rem;color:#8b949e" data-i18n="audioDelay">Audio delay (ms):</label>
<input type="number" id="ta-lat-dlna-offset" value="0" min="-5000" max="5000" step="50" style="width:80px">
<button data-icon="💾" data-i18n="saveApply" onclick="taSetLatency('dlna_output_offset_ms',$('#ta-lat-dlna-offset').value)">💾 Save + Apply</button>
<span class="media-meta">Applies mpv audio-delay in milliseconds for DLNA sync. Positive delays audio; negative advances audio/video sync.</span></div></div>
<div class="sec"><h3 data-i18n="diagnostics">Diagnostics</h3><div id="ta-summary" class="media-meta">Click Refresh</div><details style="margin-top:.5rem"><summary class="media-meta" style="cursor:pointer">Raw technical JSON</summary><pre id="ta-raw">Click Refresh</pre></details></div>
</div>
<div id="p-devices" class="pnl">
<div class="sec"><div class="media-head"><div><h3 data-i18n="devicesTitle">Devices</h3><div class="media-meta" data-i18n="devicesDesc">Pair and connect hardware here. Speaker output routing and volume remain in Audio.</div></div><div class="row"><button data-i18n="refresh" data-icon="🔄" onclick="devicesRefresh()">🔄 Refresh</button></div></div></div>
<div class="media-grid"><div class="sec"><h3 data-i18n="btPair">Bluetooth Pairing</h3><div class="row"><button onclick="deviceBtScan()">🔍 Scan</button><span id="dev-bt-status" class="media-meta">—</span></div><div id="dev-bt-list" data-i18n="clickScanRefresh" class="media-meta" style="margin-top:.4rem">Click Scan or Refresh</div></div>
<div class="sec"><h3 data-i18n="wifiConfig">Wi-Fi Configuration</h3><div class="row"><button onclick="wifiStatus()">📶 Status</button><button onclick="wifiScan()">🔍 Scan Wi-Fi</button></div><div class="row" style="margin-top:.35rem"><input id="wifi-ssid" data-i18n="ssid" data-i18n-attr="placeholder" placeholder="SSID" style="flex:1"><input id="wifi-pass" data-i18n="password" data-i18n-attr="placeholder" type="password" placeholder="Password (kept in browser only)" style="flex:1"><button data-i18n="connect" onclick="wifiConnect()">Connect</button></div><div id="wifi-list" class="media-meta" style="margin-top:.4rem">—</div></div></div>
<div class="sec"><h3 data-i18n="roles">Suggested Device Roles</h3><div class="media-meta" data-i18n="rolesDesc">• Speakers/headphones/soundbars: pair/connect/trust here, then choose routing in Audio.<br>• Xbox controllers/gamepads: pair/connect/trust here for input use; no audio routing is applied.<br>• Remote microphone and USB Alexa input are shown in Audio as sources.<br>• Future additions: HDMI-CEC device inventory, Tailscale status, storage/USB device health.</div></div>
</div>
<div id="p-terminal" class="pnl"><div class="sec">
<div class="row" style="margin-bottom:.4rem"><button data-i18n="termConnect" data-icon="🔌" onclick="termConnect()">🔌 Connect</button><button data-i18n="termDisconnect" data-icon="⏹" onclick="termDisconnect()" class="danger">⏹ Disconnect</button><span id="term-status" data-i18n="disconnected" style="font-size:.75em;color:#8b949e">Disconnected</span></div>
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
            elif path=="/selftest/testaudio": self.sj(200,selftest_testaudio())
            elif path=="/audio/state": self.sj(200,audio_state())
            elif path=="/audio/volume":
                kind=(q.get("kind")or[""])[0].strip()
                name=(q.get("name")or[""])[0].strip()
                vol=(q.get("volume")or["100"])[0].strip()
                self.sj(200,audio_set_volume(kind,name,vol))
            elif path=="/audio/mute":
                kind=(q.get("kind")or[""])[0].strip()
                name=(q.get("name")or[""])[0].strip()
                if not kind or not name: return self.sj(400,{"error":"kind and name required"})
                r=_run(["pactl","set-"+kind+"-mute",name,"toggle"], t=5)
                self.sj(200,{"ok":r.returncode==0,"out":(r.stdout+r.stderr).strip()[:200]})
            elif path=="/audio/default-sink":
                name=(q.get("name")or[""])[0].strip()
                self.sj(200,audio_set_default(name))
            elif path=="/audio/latency":
                key=(q.get("key")or[""])[0].strip()
                value=(q.get("value")or["0"])[0].strip()
                self.sj(200,audio_set_latency(key,value))
            elif path=="/dlna/select":
                name=(q.get("name")or[""])[0].strip()
                location=(q.get("location")or[""])[0].strip()
                usn=(q.get("usn")or[""])[0].strip()
                self.sj(200,audio_select_dlna_renderer(name,location,usn))
            elif path=="/dlna/connect":
                self.sj(200,audio_connect_dlna())
            elif path=="/dlna/disconnect":
                self.sj(200,audio_disconnect_dlna())
            elif path=="/keepalive":
                action=(q.get("action")or["status"])[0].strip()
                sink=(q.get("sink")or[""])[0].strip()
                self.sj(200,audio_keepalive(action,sink))
            elif path=="/audio/route/alexa-bt":
                a=(q.get("action")or["status"])[0].strip()
                if a=="status": return self.sj(200,{"ok":True,"route":"alexa_to_bt","on":bool(_loopback_module_id()),"module_id":_loopback_module_id()})
                self.sj(200,audio_route_alexa_bt(a))
            elif path=="/audio/bt":
                if _pa_dlna_running(): audio_disconnect_dlna()
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
                if _pa_dlna_running(): audio_disconnect_dlna()
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
            elif path=="/devices/state": self.sj(200,devices_state())
            elif path=="/devices/bt/scan":
                seconds=(q.get("seconds")or["5"])[0]
                self.sj(200,bluetooth_scan_devices(seconds))
            elif path=="/wifi/status": self.sj(200,wifi_status())
            elif path=="/wifi/scan": self.sj(200,wifi_scan())
            elif path=="/wifi/connect":
                ssid=(q.get("ssid")or[""])[0]
                password=(q.get("password")or[""])[0]
                self.sj(200,wifi_connect(ssid,password))
            elif path=="/youtube/cookies/status": self.sj(200,youtube_cookie_status())
            elif path=="/youtube/age-check":
                u=(q.get("url")or[""])[0].strip()
                self.sj(200,youtube_age_check(u))
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
                            current["location"]=l.split(":",1)[1].strip()
                    if current: devices.append(current)
                    # Filter MediaRenderer
                    renderers=[d for d in devices if "MediaRenderer" in d.get("usn","")]
                    for rd in renderers:
                        usn=rd.get("usn","")
                        rd["name"]=usn.split("::")[0].replace("uuid:","")[:24]
                        loc=rd.get("location","")
                        rd["host"]=(loc.split(":")[1] if":" in loc else "").replace("//","")
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
                out=(r.stdout+r.stderr).strip()[:300]
                bt_sink=None
                for _ in range(10):
                    bt_sink=next((s["name"] for s in _pactl_lines("sinks") if s["name"].startswith("bluez_")),None)
                    if bt_sink: break
                    time.sleep(1)
                if bt_sink: _keepalive_start(bt_sink)
                self.sj(200,{"result":out,"bt_sink":bt_sink,"keepalive":_keepalive_status()})
            elif path=="/bt/disconnect":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                r=subprocess.run(["bluetoothctl","disconnect",mac],capture_output=True,text=True,timeout=5)
                _keepalive_stop()
                self.sj(200,{"result":(r.stdout+r.stderr).strip()[:300],"keepalive":_keepalive_status()})
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
