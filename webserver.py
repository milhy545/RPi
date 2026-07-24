#!/usr/bin/env python3
"""RPi-TV v4.2 — fixed title, no black screen, fast CEC."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlsplit, urlunsplit
import json, os, re, socket, sys, subprocess, time, stat, ssl, shutil
import asyncio, threading
from typing import Dict
try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

# yt-dlp is installed in venv, no need for Kodi addon path

from config import (
    HOST, PORT, HTTP_PORT, HTTPS_PORT, HTTPS_PORT_ALT, ALLOWED_SUBNETS,
    MAX_SOCKET_BUFFER, SOCKET_RECV_SIZE,
    KODI_HOST, KODI_PORT, MPV_SOCKET, WS_PORT, PA_DLNA_PORT, AUDIO_STATE_CACHE_TTL
)
from rpi_dashboard.api import middleware as api_middleware
from rpi_dashboard.api.routes import get_route
from rpi_dashboard.services import devices as devices_service
HTTPS_CERT_DIR = os.path.join(os.path.expanduser("~"), ".config", "rpi-dashboard", "https")
HTTPS_CERT_FILE = os.path.join(HTTPS_CERT_DIR, "webui.crt")
HTTPS_KEY_FILE = os.path.join(HTTPS_CERT_DIR, "webui.key")
HTTPS_SAN_FILE = os.path.join(HTTPS_CERT_DIR, "webui.san")
KODI_H, KODI_P = KODI_HOST, KODI_PORT
MSOCK = MPV_SOCKET

YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?.*?[?&]?v=|embed/|shorts/))([A-Za-z0-9_-]{11})")

QUALITY = {
    "360p": "best[height<=360][ext=mp4]/best[height<=360]",
    "480p": "best[height<=480][ext=mp4]/best[height<=480]",
    "720p": "best[height<=720][ext=mp4]/best[height<=720]",
    "1080p":"best[height<=1080][ext=mp4]/best[height<=1080]",
}
DQ = "720p"

def norm(u: str) -> str:
    """Normalize URL by removing redundant slashes in path."""
    if not isinstance(u, str):
        return ""
    u=u.strip()
    try: p=urlsplit(u)
    except Exception: return u
    if p.scheme in ("http","https"): return urlunsplit((p.scheme,p.netloc,re.sub(r"/{2,}","/",p.path),p.query,p.fragment))
    return u

def yt_id(u: str) -> str:
    """Extract YouTube video ID from URL."""
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
            while len(d)<MAX_SOCKET_BUFFER:
                c=s.recv(SOCKET_RECV_SIZE)
                if not c: break
                d+=c
                if b"\n" in d: break
            dec=json.JSONDecoder(); probe=d.decode("utf-8","replace").lstrip()
            while probe:
                try: obj,i=dec.raw_decode(probe)
                except Exception: break
                if isinstance(obj,dict) and obj.get("id")==1: return obj
                probe=probe[i:].lstrip()
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {"result":[]}

# ── MPV ────────────────────────────────────────────────────────────────

_mpv=None; _mq=DQ; _mtitle=""; _murl=""

def mcmd(*a):
    if not os.path.exists(MSOCK): return {"error":"not running"}
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(MSOCK); s.settimeout(2)
        s.sendall((json.dumps({"command":list(a)})+"\n").encode())
        d=b""
        while True:
            c=s.recv(SOCKET_RECV_SIZE)
            if not c: break
            d+=c
            if b"\n" in d: break
        s.close(); return json.loads(d.decode().strip().split("\n")[-1])
    except Exception as e: return {"error":str(e)}

def mget(p): return mcmd("get_property",p)

def _mpv_pids_for_socket(path=MSOCK):
    try:
        r=subprocess.run(["pgrep","-af","mpv"],capture_output=True,text=True,timeout=3)
    except Exception:
        return []
    pids=[]
    needle=f"--input-ipc-server={path}"
    for line in r.stdout.splitlines():
        parts=line.split(maxsplit=1)
        if len(parts)<2: continue
        if needle in parts[1]:
            try: pids.append(int(parts[0]))
            except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return pids

def _terminate_pids(pids, timeout=3.0):
    stopped=[]
    for pid in sorted(set(pids)):
        try:
            os.kill(pid, 15)
            stopped.append({"pid":pid,"signal":"TERM"})
        except ProcessLookupError:
            stopped.append({"pid":pid,"signal":"missing"})
        except Exception as e:
            stopped.append({"pid":pid,"error":str(e)})
    deadline=time.time()+timeout
    while time.time()<deadline:
        alive=[pid for pid in set(pids) if os.path.exists(f"/proc/{pid}")]
        if not alive: break
        time.sleep(0.1)
    for pid in sorted(set(pids)):
        if os.path.exists(f"/proc/{pid}"):
            try:
                os.kill(pid, 9)
                stopped.append({"pid":pid,"signal":"KILL"})
            except ProcessLookupError:
                pass
            except Exception as e:
                stopped.append({"pid":pid,"kill_error":str(e)})
    return stopped

def mpv_start(url, q=None, resume=False):
    global _mpv,_mq,_mtitle,_murl
    # Force HDMI connector + activate HDMI audio profile
    try:
        with open("/sys/class/drm/card0-HDMI-A-1/status", "w") as f: f.write("on")
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    import subprocess as _sp
    _sp.run(["pactl","set-card-profile","alsa_card.platform-3f902000.hdmi","output:hdmi-stereo"],
            capture_output=True, timeout=3)
    _sp.run(["pactl","set-default-sink","alsa_output.platform-3f902000.hdmi.hdmi-stereo"],
            capture_output=True, timeout=3)
    if not resume and mpv_ipc_socket_live():
        save_mpv_resume_memory()
    mpv_stop(); _mq=q or _mq
    surl,meta=resolve(url,_mq)
    _murl=url
    _mtitle=meta.get("title","Playing")

    # DeepMind Strategy: mpv pinned to cores 1-2 (media.compute)
    # Escalation for HEVC/heavy: detect via format probe, use cores 1-3
    use_three_cores = False
    if meta.get("h", 0) >= 1080 or meta.get("dur", 0) > 3600:
        # 1080p+ or long content (likely high bitrate) -> use 3 cores
        use_three_cores = True

    core_mask = "1-3" if use_three_cores else "1-2"
    resume_pos = None
    if resume:
        mem = get_mpv_memory_for_url(url)
        if mem and mem.get("position") is not None:
            try:
                resume_pos = max(0.0, float(mem["position"]))
            except Exception:
                resume_pos = None
    cmd=["taskset", "-c", core_mask, "mpv",
         "--vo=drm","--drm-mode=640x480","--hwdec=v4l2m2m",
         "--fullscreen","--no-terminal","--ytdl=no","--ao=pulse",
         f"--title={_mtitle}",
         f"--input-ipc-server={MSOCK}","--keep-open=always"]
    if resume_pos is not None:
        cmd.append(f"--start={resume_pos:.3f}")
    cmd.append(surl)
    _mpv=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {"ok":True,"pid":_mpv.pid,"url":surl,"meta":meta,"q":_mq,"cores":core_mask,"resume_pos":resume_pos}

def _restore_console():
    """Restore fbcon after MPV DRM exit."""
    import subprocess as _sp
    try:
        # Find which VT the TUI is running on
        tui_pid = None
        for line in _sp.check_output(["ps","axo","pid,tty,comm"], text=True).splitlines():
            if "tui.py" in line and "bash" not in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "?":
                    tui_pid = parts[1]
                    break
        target_vt = "/dev/tty1"  # fallback
        if tui_pid:
            tty = _sp.check_output(["ps","-o","tty=","-p",tui_pid], text=True).strip()
            if tty and tty != "?":
                target_vt = f"/dev/{tty}"
        # Activate the TUI's VT to restore console
        _sp.run(["setfont"], capture_output=True, timeout=2)
        _sp.run(["chvt","1"], capture_output=True, timeout=2)
        # Try to rebind fbcon
        _sp.run(["sh","-c","echo 0 > /sys/class/vt/vtblank"], capture_output=True, timeout=2)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)

def mpv_stop():
    global _mpv
    pids=[]
    if _mpv and _mpv.poll() is None:
        pids.append(_mpv.pid)
    pids.extend(_mpv_pids_for_socket(MSOCK))
    if mpv_ipc_socket_live():
        try: save_mpv_resume_memory()
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
        try: mcmd("quit")
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
        time.sleep(0.3)
    stopped=_terminate_pids(pids)
    _mpv=None
    cleanup_stale_mpv_socket()
    time.sleep(0.5)
    _restore_console()
    return {"ok":True,"stopped":stopped,"pids":sorted(set(pids)),"socket_live":mpv_ipc_socket_live()}

def mpv_st():
    tracked=_mpv and _mpv.poll() is None
    pids=_mpv_pids_for_socket(MSOCK)
    if not tracked and not mpv_ipc_socket_live() and not pids: return {"on":False}
    try:
        return {"on":True,"pid":(_mpv.pid if tracked else (pids[0] if pids else None)),"pids":pids,"tracked":bool(tracked),"orphan":not bool(tracked),
            "paused":mget("pause").get("data",False),
            "pos":mget("time-pos").get("data",0),
            "dur":mget("duration").get("data",0),
            "title":_mtitle or mget("media-title").get("data",""),
            "vol":mget("volume").get("data",100),"q":_mq}
    except Exception: return {"on":True,"err":True,"pid":(_mpv.pid if tracked else (pids[0] if pids else None)),"pids":pids,"tracked":bool(tracked),"orphan":not bool(tracked),"title":_mtitle}

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
    except Exception: return "Timeout"
_bridg = None
def br_start():
    global _bridg
    br_stop()
    sc=r'''
import subprocess,json,os,socket,select,time,sys
MP="/tmp/rpi-mpv.sock"
def mc(c):
    if not os.path.exists(MP): return
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(MP);s.settimeout(1)
        s.sendall((json.dumps({"command":["parse-command",c]})+"\n").encode());s.recv(SOCKET_RECV_SIZE);s.close()
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    try: p.wait(timeout=2)
    except Exception: p.kill()
    time.sleep(2)
'''
    _bridg=subprocess.Popen([sys.executable,"-c",sc],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {"ok":True,"pid":_bridg.pid}

def br_stop():
    global _bridg
    if _bridg and _bridg.poll() is None:
        _bridg.terminate()
        try: _bridg.wait(timeout=3)
        except Exception: _bridg.kill()
    _bridg=None

def br_st():
    return {"on":_bridg is not None and _bridg.poll() is None,"pid":_bridg.pid if _bridg else None}

# ── Audio state/routing helpers ───────────────────────────────────────
USB_ALEXA_SRC="alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback"
BT_SOUNDBAR_MAC="24:4B:03:92:0B:8C"
BT_SOUNDBAR_NAME="[Samsung] Soundbar J-Series"
BT_SOUNDBAR_SINK="bluez_output.24_4B_03_92_0B_8C.1"
HDMI_SINK="alsa_output.platform-3f00b840.mailbox.stereo-fallback"
DLNA_SINK_KEYWORDS=["uuid_","WiiMu","LinkPlayer","Sphere","TIBO"]
AUDIO_LATENCY_FILE=os.path.expanduser("~/rpi-dashboard/.audio-latency.json")
SILENT_WAV="/tmp/rpi-silent-48k.wav"
PA_DLNA_LOG="/tmp/pa-dlna-webui.log"
_PA_DLNA_PORT = PA_DLNA_PORT
_pa_dlna_proc=None
_ka_procs: Dict[str, subprocess.Popen] = {}  # sink_name -> subprocess.Popen
_audio_state_cache={"ts": 0.0, "data": None}
_audio_state_lock=threading.Lock()
AUDIO_STATE_CACHE_TTL = AUDIO_STATE_CACHE_TTL


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
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def _find_loopback_by_source(source_name):
    """Find loopback module ID for a given source."""
    try:
        r=_run(["pactl","list","short","modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and source_name in l:
                return l.split()[0]
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def _find_loopbacks():
    """Find all active loopback modules."""
    loops=[]
    try:
        r=_run(["pactl","list","short","modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l:
                parts=l.split()
                mod_id=parts[0]
                # Parse source and sink from module args
                m=re.search(r'source=(\S+)', l)
                src=m.group(1) if m else None
                m=re.search(r'sink=(\S+)', l)
                snk=m.group(1) if m else None
                loops.append({"id":mod_id,"source":src,"sink":snk})
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return loops

def _start_loopback(source, sink, rate=48000, channels=2):
    """Start a PipeWire loopback from source to sink. Returns module ID."""
    r=_run(["pactl","load-module","module-loopback",
            f"source={source}",f"sink={sink}",
            f"rate={rate}",f"channels={channels}",
            "channel_map=front-left,front-right",
            "source_dont_move=true","sink_dont_move=true",
            "latency_msec=20","remix=true"], t=10)
    if r.returncode==0:
        try: return int(r.stdout.strip())
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def _stop_loopback(module_id):
    """Stop a specific loopback module."""
    if not module_id: return False
    r=_run(["pactl","unload-module",str(module_id)], t=5)
    return r.returncode==0

def _stop_loopback_by_source(source_name):
    """Stop loopback(s) for a given source."""
    stopped=False
    for lb in _find_loopbacks():
        if lb["source"]==source_name:
            if _stop_loopback(lb["id"]): stopped=True
    return stopped

def _get_default_sink():
    """Get current default sink."""
    try: return _run(["pactl","get-default-sink"]).stdout.strip()
    except Exception: return None

def _resolve_alexa_target():
    """Determine where Alexa AUX should route based on default sink.
    Follows primary source. Fallback: BT > DLNA > HDMI > AUX Out.
    """
    ds=_get_default_sink()
    if ds and ds not in ("", "none"):
        return ds
    # Fallback order
    sinks=_pactl_lines("sinks")
    names=[s["name"] for s in sinks]
    for candidate in [BT_SOUNDBAR_SINK] + [n for n in names if any(k in n for k in DLNA_SINK_KEYWORDS)] + [HDMI_SINK]:
        if candidate in names:
            return candidate
    return names[0] if names else None

# ── DLNA Input routing state ─────────────────────────────────────────
_DLNAIN_MODE_FILE=os.path.expanduser("~/rpi-dashboard/.dlnain-mode.json")

def _load_dlnain_mode():
    try:
        with open(_DLNAIN_MODE_FILE) as f: return json.load(f)
    except Exception: return {"mode":"follow","manual_sink":None}

def _save_dlnain_mode(data):
    try:
        with open(_DLNAIN_MODE_FILE,"w") as f: json.dump(data,f)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)

def _resolve_dlnain_target():
    """Determine DLNA Input target based on mode."""
    cfg=_load_dlnain_mode()
    if cfg.get("mode")=="manual" and cfg.get("manual_sink"):
        return cfg["manual_sink"]
    # Follow primary
    return _resolve_alexa_target()

def _dlnain_loopback_running():
    """Check if DLNA Input loopback (gmrender source) is active."""
    gmrender_src=None
    try:
        r=_run(["pactl","list","short","sources"])
        for l in r.stdout.splitlines():
            if "gmediarender" in l.lower() or "gmrender" in l.lower():
                parts=l.split()
                if len(parts)>=2: gmrender_src=parts[1]
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    if not gmrender_src: return False, None
    lb=_find_loopback_by_source(gmrender_src)
    return lb is not None, gmrender_src

def _alexa_loopback_running():
    """Check if Alexa AUX loopback is active. Returns (running, current_target)."""
    try:
        r=_run(["pactl","list","short","modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and USB_ALEXA_SRC in l:
                m=re.search(r'sink=(\S+)', l)
                target=m.group(1) if m else None
                m2=re.search(r'^(\d+)', l)
                mod_id=m2.group(1) if m2 else None
                return True, target, mod_id
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return False, None, None

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
            with open(AUDIO_LATENCY_FILE) as f:
                return json.load(f)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {"dlna_output_offset_ms": 0, "default_latency_ms": 0}

def _save_audio_latency(data):
    try:
        with open(AUDIO_LATENCY_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)

# ------- Report handling -------
def _save_report(report: dict, client_ip: str) -> str:
    """Save a bug/feature report to the local `reports/` directory.
    Returns the filename used for storage.
    """
    import time, json, os
    ts = int(time.time())
    filename = f"{ts}_{client_ip.replace('.','_')}.json"
    path = os.path.join(os.path.dirname(__file__), "reports", filename)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Log error to stderr but do not crash server
        print(f"[WARN] Failed to save report: {e}", file=sys.stderr)
    return filename

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
                # Check if this is a keepalive process (pw-cat with silent WAV)
                is_keepalive=False
                try:
                    pr=_run(["ps","-o","args=","-p",client_pid],t=2)
                    if pr.returncode==0 and "pw-cat" in pr.stdout and SILENT_WAV in pr.stdout:
                        is_keepalive=True
                except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
                out.append({"id":p[0],"sink_id":sink_id,"sink":sink_label,"client":client_pid,"format":p[4] if len(p)>4 else "","keepalive":is_keepalive})
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
def get_audio_matrix():
    import json, subprocess
    try:
        d = json.loads(subprocess.run(["pw-dump"], capture_output=True, timeout=5).stdout)
    except Exception:
        return {"nodes": {}, "links": []}
    nodes = {}
    for obj in d:
        if obj.get("type") == "PipeWire:Interface:Node":
            nid = obj.get("id")
            props = obj.get("info", {}).get("props", {})
            name = props.get("node.name", "")
            desc = props.get("node.description", name)
            klass = props.get("media.class", "")
            if "Audio" in klass:
                nodes[nid] = {"id": nid, "name": name, "desc": desc, "class": klass}
    links = set()
    for obj in d:
        if obj.get("type") == "PipeWire:Interface:Link":
            info = obj.get("info", {})
            # Include links regardless of state (active, init, paused, etc.)
            if info.get("output-node-id") and info.get("input-node-id"):
                links.add((info.get("output-node-id"), info.get("input-node-id")))
    # Add synthetic links for module-loopback (used for DLNA routing)
    try:
        import subprocess
        r_mod = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True, timeout=2)
        for line in r_mod.stdout.splitlines():
            if "module-loopback" in line and "source=" in line and "sink=" in line:
                parts = line.split()
                src_name = next((p.split("=")[1] for p in parts if p.startswith("source=")), None)
                snk_name = next((p.split("=")[1] for p in parts if p.startswith("sink=")), None)
                src_id = next((n["id"] for n in nodes.values() if n["name"] == src_name), None)
                snk_id = next((n["id"] for n in nodes.values() if n["name"] == snk_name), None)
                if src_id and snk_id:
                    links.add((src_id, snk_id))
    except: pass

    return {"nodes": nodes, "links": list(links)}

def audio_matrix_link(out_n, in_n, state):
    import subprocess
    is_dlna = "-uuid:" in in_n
    
    if is_dlna:
        if state == "1":
            r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
            if f"source={out_n}" in r.stdout and f"sink={in_n}" in r.stdout:
                return {"ok": True, "out": "already linked via loopback"}
            cmd = ["pactl", "load-module", "module-loopback", f"source={out_n}", f"sink={in_n}"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return {"ok": r.returncode == 0, "out": r.stdout.strip()[:200]}
        else:
            r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
            unloaded = False
            for line in r.stdout.splitlines():
                if "module-loopback" in line and f"source={out_n}" in line and f"sink={in_n}" in line:
                    mod_id = line.split()[0]
                    subprocess.run(["pactl", "unload-module", mod_id])
                    unloaded = True
            return {"ok": True, "out": "unloaded" if unloaded else "not found"}
            
    cmd = ["pw-link", out_n, in_n] if state == "1" else ["pw-link", "-d", out_n, in_n]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=1.5)
        out_str = (r.stdout+r.stderr).decode('utf-8','ignore').strip()
        ok = (r.returncode == 0) or ("File exists" in out_str and state == "1")
        return {"ok": ok, "out": out_str[:200]}
    except subprocess.TimeoutExpired:
        return {"ok": True, "out": "already linked"}


def audio_set_volume(kind, name, volume):
    if kind not in ("sink", "source"): return {"ok":False,"error":"kind must be sink or source"}
    if not name: return {"ok":False,"error":"name required"}
    vol, err = _parse_int(volume, "volume")
    if err: return err
    vol=max(0, min(150, vol))
    cmd=["pactl","set-"+kind+"-volume",name,str(vol)+"%"]
    r=_run(cmd, t=5)
    
    if kind == "sink":
        try:
            sinks = _run(["pactl", "list", "short", "sinks"]).stdout.splitlines()
            sink_id = None
            for line in sinks:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == name:
                    sink_id = parts[0]
                    break
            if sink_id:
                inputs = _run(["pactl", "list", "short", "sink-inputs"]).stdout.splitlines()
                for line in inputs:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == sink_id:
                        _run(["pactl", "set-sink-input-volume", parts[0], str(vol)+"%"])
        except Exception:
            pass

    return {"ok":r.returncode==0,"kind":kind,"name":name,"volume":vol,"out":(r.stdout+r.stderr).strip()[:200]}

def audio_set_default(name):
    if not name:
        return {"ok": False, "error": "name required"}
    # Use default timeout (5s) by not passing t
    r = _run(["pactl", "set-default-sink", name])
    return {"ok": r.returncode == 0, "name": name, "out": (r.stdout + r.stderr).strip()[:200]}

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
    with wave.open(SILENT_WAV,'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000)
        f.writeframes(struct.pack('<'+'h'*48000, *([0]*48000)))

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
            except Exception: proc.kill()
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
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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
            except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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
            except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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
        with open(PA_DLNA_LOG, "ab") as log:
            _pa_dlna_proc=subprocess.Popen(["pa-dlna","--nics","eth0","--loglevel","info","--port",_PA_DLNA_PORT],stdout=log,stderr=log)
        return True
    except Exception:
        return False

# ── DLNA Renderer (gmediarender) ──────────────────────────────────────

def _gmrender_running():
    """Check if gmediarender is running."""
    try:
        r=subprocess.run(["pgrep","-f","gmediarender"],capture_output=True,text=True,timeout=2)
        return r.returncode==0 and bool(r.stdout.strip())
    except Exception: return False

def _gmrender_pid():
    """Get gmediarender PID."""
    try:
        r=subprocess.run(["pgrep","-f","gmediarender"],capture_output=True,text=True,timeout=2)
        if r.returncode==0 and r.stdout.strip():
            return int(r.stdout.strip().splitlines()[0])
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def _gmrender_uptime(pid):
    """Get process uptime in seconds."""
    if not pid: return None
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts=f.read().split()
        start_ticks=int(parts[21])
        import os as _os
        clk=_os.sysconf(_os.sysconf_names['SC_CLK_TCK'])
        with open('/proc/uptime') as f:
            uptime=float(f.read().split()[0])
        start_sec=uptime-(start_ticks/clk)
        return int(uptime-start_sec)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def dlna_renderer_status():
    """Get DLNA renderer status."""
    running=_gmrender_running()
    pid=_gmrender_pid()
    uptime=_gmrender_uptime(pid) if pid else None
    installed=bool(shutil.which("gmediarender"))
    pw_ok=False
    try:
        r=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True,timeout=3)
        pw_ok=r.returncode==0
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {
        "ok":True,
        "running":running,
        "pid":pid,
        "uptime":uptime,
        "installed":installed,
        "pipewire":pw_ok,
        "name":"RPi Renderer",
        "ready":installed and pw_ok
    }

def dlna_renderer_start():
    """Start gmediarender service."""
    if _gmrender_running():
        return {"ok":True,"already":True,"status":dlna_renderer_status()}
    r=subprocess.run(["systemctl","start","gmrender-resurrect"],capture_output=True,text=True,timeout=10)
    if r.returncode==0:
        time.sleep(2)
        return {"ok":True,"method":"systemd","status":dlna_renderer_status()}
    return {"ok":False,"error":(r.stdout+r.stderr).strip()[:300],"status":dlna_renderer_status()}

def dlna_renderer_stop():
    """Stop gmediarender service."""
    if not _gmrender_running():
        return {"ok":True,"was_running":False,"status":dlna_renderer_status()}
    r=subprocess.run(["systemctl","stop","gmrender-resurrect"],capture_output=True,text=True,timeout=10)
    if r.returncode==0:
        time.sleep(1)
        return {"ok":True,"method":"systemd","status":dlna_renderer_status()}
    pid=_gmrender_pid()
    if pid:
        try:
            os.kill(pid,15)
            time.sleep(1)
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {"ok":not _gmrender_running(),"method":"signal","status":dlna_renderer_status()}

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

# ── Routing: retarget and DLNA Input ─────────────────────────────────

def _retarget_alexa():
    """Retarget Alexa loopback to follow current default_sink."""
    running,target,mid=_alexa_loopback_running()
    if not running:
        return {"ok":False,"error":"Alexa loopback not running"}
    new_target=_resolve_alexa_target()
    if not new_target:
        return {"ok":False,"error":"No suitable output found"}
    if target==new_target:
        return {"ok":True,"unchanged":True,"target":target}
    # Stop old, start new
    _stop_loopback(mid)
    time.sleep(0.3)
    new_mid=_start_loopback(USB_ALEXA_SRC, new_target)
    if new_mid:
        return {"ok":True,"old_target":target,"new_target":new_target,"module_id":new_mid}
    return {"ok":False,"error":"Failed to start loopback to new target","old_target":target}

def _dlnain_start():
    """Start DLNA Input loopback from gmrender source."""
    running,src=_dlnain_loopback_running()
    if running:
        return {"ok":True,"already":True,"source":src}
    # Find gmrender source
    gmrender_src=None
    try:
        r=_run(["pactl","list","short","sources"])
        for l in r.stdout.splitlines():
            if "gmediarender" in l.lower() or "gmrender" in l.lower():
                parts=l.split()
                if len(parts)>=2: gmrender_src=parts[1]
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    if not gmrender_src:
        return {"ok":False,"error":"gmrender source not found in PipeWire"}
    target=_resolve_dlnain_target()
    if not target:
        return {"ok":False,"error":"No suitable output found"}
    mid=_start_loopback(gmrender_src, target)
    if mid:
        return {"ok":True,"source":gmrender_src,"target":target,"module_id":mid}
    return {"ok":False,"error":"Failed to start loopback"}

def _dlnain_stop():
    """Stop DLNA Input loopback."""
    running,src=_dlnain_loopback_running()
    if not running:
        return {"ok":True,"was_running":False}
    stopped=_stop_loopback_by_source(src)
    return {"ok":stopped,"source":src}

def _dlnain_retarget(new_target):
    """Retarget DLNA Input loopback to new sink."""
    running,src=_dlnain_loopback_running()
    if not running: return False
    # Find and stop current
    lb=_find_loopback_by_source(src)
    if lb: _stop_loopback(lb["id"])
    time.sleep(0.3)
    # Start new
    mid=_start_loopback(src, new_target)
    return mid is not None

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
    return devices_service._bt_device_kind(name)

def _bt_paired_devices():
    return devices_service._bt_paired_devices()

def _bt_scanned_devices():
    return devices_service._bt_scanned_devices()

def devices_state():
    audio=audio_state()
    state=devices_service.devices_state()
    state["audio_devices"]=audio.get("devices",{})
    state["default_sink"]=audio.get("default_sink")
    return state

def bluetooth_scan_devices(seconds=5):
    return devices_service.bluetooth_scan_devices(seconds)

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
    if password:
        cmd = ["nmcli", "--ask", "device", "wifi", "connect", ssid]
        try:
            r = subprocess.run(cmd, input=password + "\n", capture_output=True, text=True, timeout=30)
        except Exception as e:
            return {"ok": False, "error": f"nmcli failed: {e}"}
    else:
        cmd = ["nmcli", "device", "wifi", "connect", ssid]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as e:
            return {"ok": False, "error": f"nmcli failed: {e}"}
    return {"ok":r.returncode==0,"out":(r.stdout+r.stderr).strip()[:300]}

def kodi_status():
    bins={name: (shutil.which(name) or "") for name in ("kodi","kodi-standalone")}
    port=subprocess.run(["sh","-lc",f"ss -tln 2>/dev/null | grep -q ':{KODI_P} '"],capture_output=True,text=True,timeout=3).returncode==0
    rpc=kodi_rpc("Player.GetActivePlayers", t=1)
    installed=bool(bins.get("kodi") or bins.get("kodi-standalone"))
    reachable=("error" not in rpc) and (port or rpc.get("result") is not None)
    useful=installed and reachable
    decision="keep-diagnostics-only" if not useful else "keep-launcher"
    recommendation="Use Player/mpv for normal playback. Kodi is not installed or not listening on JSON-RPC 9090." if not useful else "Kodi JSON-RPC is available; legacy launcher can be used for renderer experiments."
    return {"ok":True,"installed":installed,"binaries":bins,"jsonrpc_port":KODI_P,"port_listening":port,"rpc":rpc,"useful":useful,"decision":decision,"recommendation":recommendation}

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

def media_preview(url):
    if not url: return {"ok":False,"error":"url required"}
    url=norm(url)
    vid=yt_id(url)
    if not vid:
        p=urlsplit(url)
        title=os.path.basename(p.path.rstrip("/")) or p.netloc or url[:80]
        return {"ok":True,"type":"direct","url":url,"title":title[:120],"thumbnail":"","duration":None}
    try:
        import yt_dlp as youtube_dl
        _co=os.path.join(os.path.dirname(os.path.abspath(__file__)),"yt-cookies.txt")
        _opts={"quiet":True,"no_warnings":True,"noplaylist":True,"skip_download":True,
               "extract_flat":False,"socket_timeout":8,
               "extractor_args":{"youtube":{"player_client":["default","android","web"]}}}
        if os.path.exists(_co): _opts["cookiefile"]=_co
        with youtube_dl.YoutubeDL(_opts) as y:
            info=y.extract_info(f"https://youtu.be/{vid}", download=False)
        thumbs=info.get("thumbnails") or []
        thumb=info.get("thumbnail") or (thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg")
        return {"ok":True,"type":"youtube","id":vid,"url":url,"title":info.get("title") or f"YouTube {vid}","thumbnail":thumb,"duration":info.get("duration"),"uploader":info.get("uploader")}
    except Exception as e:
        return {"ok":False,"type":"youtube","id":vid,"error":str(e)[:400],"thumbnail":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}

def selftest_testaudio():
    html_doc=page()
    required=[
        'data-t="audio"', 'data-t="devices"', 'id="p-player"', 'id="p-audio"', 'id="p-devices"',
        'id="ta-sinks"', 'id="ta-sources"', 'id="ta-mixer"',
        'id="ta-routes"', 'id="ta-summary"', 'id="ta-raw"', 'id="yt-cookie-status"',
        'id="player-preview"', 'function previewUrl()', 'function tryClipboardUrl(',
        "onclick=\"sw('player')\"", "sw('audio');taRefresh()",
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

CSS="""*{box-sizing:border-box}body{font-family:system-ui,sans-serif;width:min(1440px,98vw);max-width:none;margin:0 auto;padding:.6rem;background:#0d1117;color:#c9d1d9;font-size:14px;overflow-x:hidden}
input,button,select{font-size:.9rem;padding:.5rem .65rem;margin:.1rem 0;border-radius:.3rem;border:1px solid #30363d;background:#161b22;color:#c9d1d9}
input,select{width:100%}button{cursor:pointer;background:#21262d}button:hover{background:#30363d;border-color:#58a6ff}
input[type=range]{min-height:24px;padding:0}
button:active{background:#1a5276}button.on{background:#1a5276;border-color:#58a6ff}button.danger{border-color:#f85149;color:#f85149}
.row{display:flex;gap:.3rem;flex-wrap:wrap;align-items:center}a{color:#58a6ff}
.url-wrap{position:relative;flex:1;min-width:220px}.url-wrap input{padding-right:2.7rem}.url-paste{position:absolute;right:.18rem;top:50%;transform:translateY(-50%);width:2.05rem;height:2.05rem;margin:0;padding:0;display:flex;align-items:center;justify-content:center;border-radius:.25rem;font-size:1rem;line-height:1;background:#21262d}
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
.lang-btn{font-size:.78rem;padding:.22rem .42rem;border-radius:999px;line-height:1;border:1px solid #30363d;background:#161b22;color:#c9d1d9;min-width:2.25rem;min-height:2.25rem;display:inline-flex;align-items:center;justify-content:center}
.lang-btn.active{background:#1a5276;border-color:#58a6ff;color:#fff}
#toast{position:fixed;bottom:12px;right:12px;z-index:999;max-width:300px;display:flex;flex-direction:column;gap:4px;pointer-events:none}
#security-banner{display:none;margin:.35rem 0 .55rem;padding:.45rem .6rem;border:1px solid #30363d;border-radius:.45rem;background:#161b22;color:#c9d1d9;font-size:.82rem;align-items:center;justify-content:space-between;gap:.6rem;flex-wrap:wrap}
#security-banner.show{display:flex}#security-banner.warn{border-color:#d29922;background:#2d2308}#security-banner.ok{border-color:#238636;background:#0d2818;color:#3fb950}#security-banner a{font-weight:700;white-space:nowrap;display:inline-flex;align-items:center;min-height:1.75rem}
.t{padding:.4rem .7rem;border-radius:.3rem;font-size:.8rem;pointer-events:auto;animation:fi .2s}
.t.ok{background:#0d2818;border:1px solid #238636;color:#3fb950}
.t.err{background:#3d1214;border:1px solid #da3633;color:#f85149}
.t.info{background:#0c2d6b;border:1px solid #1f6feb;color:#58a6ff}
@keyframes fi{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
pre{background:#161b22;padding:.6rem;border-radius:.3rem;overflow:auto;font-size:.8em;margin:.3rem 0}
#terminal{width:100%;max-width:100%;box-sizing:border-box;background:#000;padding:0;border:1px solid #30363d;border-radius:4px;height:min(70vh,720px);min-height:420px;overflow:hidden}
#terminal .xterm{height:100%;width:100%}
#terminal .xterm-viewport{overflow-y:hidden!important}
#terminal .xterm-screen{max-width:100%;width:100%!important}
.media-head{display:flex;justify-content:space-between;gap:.6rem;align-items:center;margin:.3rem 0 .7rem}
.media-grid{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}
.media-card{background:#0d1117;border:1px solid #30363d;border-radius:.55rem;padding:.65rem;min-height:96px}
#player-preview{display:none;align-items:center;gap:.6rem;margin-top:.45rem;padding:.45rem;border:1px solid #30363d;border-radius:.45rem;background:#0d1117}
#player-preview.on{display:flex}#player-preview img{width:120px;max-width:35vw;border-radius:.35rem}#player-preview-title{font-weight:700;color:#f0f6fc;margin-bottom:.15rem}
.media-card h4{margin:0 0 .4rem;font-size:.85rem;color:#f0f6fc;display:flex;justify-content:space-between;gap:.4rem}
.media-meta{font-size:.72rem;color:#8b949e;word-break:break-all;line-height:1.35}
.badge{display:inline-block;padding:.12rem .4rem;border-radius:999px;border:1px solid #30363d;font-size:.68rem;color:#8b949e}
.badge.ok{border-color:#238636;color:#3fb950;background:#0d2818}.badge.warn{border-color:#d29922;color:#d29922;background:#2d2308}.badge.err{border-color:#da3633;color:#f85149;background:#3d1214}
.meter{height:6px;background:#21262d;border-radius:999px;overflow:hidden;margin:.45rem 0}.meter span{display:block;height:100%;background:#58a6ff;width:0%}
.route-card{border-left:3px solid #58a6ff}.route-card.on{border-left-color:#3fb950}.route-card.off{border-left-color:#8b949e}
.vol-row-mixer{display:flex;align-items:center;gap:.3rem;margin:.25rem 0}.vol-row-mixer label{font-size:.72rem;color:#8b949e;min-width:48px;text-align:right}.vol-row-mixer input[type=range]{flex:1;height:6px;accent-color:#58a6ff;cursor:pointer}.vol-row-mixer button{font-size:.7rem;padding:2px 8px}
.info-btn{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;border:1px solid #8b949e;color:#8b949e;font-size:.72rem;font-style:italic;cursor:pointer;vertical-align:middle;margin-left:.3rem;background:transparent;line-height:1;padding:0;flex:0 0 24px}
.info-btn:hover,.info-btn:focus{border-color:#58a6ff;color:#58a6ff;background:rgba(88,166,255,.08)}
.tip-wrap{position:relative;display:inline-flex;align-items:center}
.tip-box{display:none;position:absolute;left:50%;transform:translateX(-50%);bottom:calc(100% + 8px);z-index:900;width:260px;max-width:90vw;padding:.55rem .7rem;background:#1c2333;border:1px solid #58a6ff;border-radius:.45rem;color:#c9d1d9;font-size:.72rem;line-height:1.4;box-shadow:0 4px 18px rgba(0,0,0,.5);pointer-events:auto;white-space:normal}
.tip-box::after{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:6px solid transparent;border-top-color:#58a6ff}
.tip-box.show{display:block}
.sec-head{display:flex;align-items:center;gap:0;flex-wrap:wrap}
.sec-head h3{margin:0}
@media(max-width:700px){.media-grid{grid-template-columns:1fr}.media-head{flex-direction:column;align-items:flex-start}}
@media(max-width:500px){.tip-box{left:0;transform:none;width:220px}.tip-box::after{left:20px}}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;padding:1rem;box-sizing:border-box}
.modal.show{display:flex}
.modal-content{background:#161b22;border:1px solid #30363d;border-radius:.5rem;width:100%;max-width:400px;padding:1rem;position:relative}
.modal-close{position:absolute;top:.5rem;right:.5rem;background:transparent;border:none;color:#8b949e;cursor:pointer;font-size:1.2rem}
.modal h3{margin-top:0;color:#c9d1d9}
.modal select, .modal textarea{width:100%;margin-bottom:.8rem;box-sizing:border-box;background:#0d1117;border:1px solid #30363d;color:#c9d1d9;padding:.4rem;border-radius:.3rem}
.modal textarea{height:100px;resize:vertical}"""

JS=r"""
function $(s){return document.querySelector(s)}function $$(s){return document.querySelectorAll(s)}
function msg(t,c){let d=document.createElement('div');d.className='t '+c;d.textContent=t;$('#toast').appendChild(d);setTimeout(()=>d.remove(),4000)}
async function api(u){try{return await(await fetch(u)).json()}catch(e){return{error:e.message}}}
function sw(n){$$('.tab').forEach(t=>t.classList.toggle('active',t.dataset.t===n));$$('.pnl').forEach(p=>p.classList.toggle('active',p.id==='p-'+n));if(n==='player'){playerEnter()}if(n==='terminal'){loadHwStats();loadSysStatus();if(term){setTimeout(termFitNow,80);setTimeout(termFitNow,250)}}}
let previewTimer=null,previewSeq=0;
function httpsUrlForCurrent(){let host=location.hostname||'rpi-tv';let p=location.port;if(p==='8080')return 'https://'+host+':8443'+location.pathname;if(p==='80'||p==='')return 'https://'+host+location.pathname;return 'https://'+host+(p?':'+p:'')+location.pathname}
function updateSecurityBanner(){let b=$('#security-banner');if(!b)return;if(location.protocol==='https:'){b.className='ok show';b.innerHTML='<span>'+L('secureClipboardEnabled')+'</span>';return}let u=httpsUrlForCurrent();b.className='warn show';b.innerHTML='<span>'+L('httpFallbackBanner')+'</span><a href="'+esc(u)+'">'+L('openHttps')+'</a>'}
function playerActive(){let p=$('#p-player');return !!(p&&p.classList.contains('active'))}
function playerEnter(){ytCookieStatus();autoClipboardUrl();schedulePreview()}
function looksMediaUrl(t){return /^https?:\/\//i.test((t||'').trim())}
async function tryClipboardUrl(manual,force){if(!navigator.clipboard||!navigator.clipboard.readText){if(manual)msg('Clipboard read is not available in this browser/context','err');return false}try{let t=(await navigator.clipboard.readText()).trim();if(looksMediaUrl(t)&&(force||!$('#url').value.trim())){$('#url').value=t;msg('URL pasted from clipboard','ok');previewUrl();return true}else if(manual){msg(looksMediaUrl(t)?'Input already has a URL':'Clipboard does not contain a media URL','info')}}catch(e){if(manual)msg('Clipboard permission denied or unavailable','err')}return false}
function pasteClipboardUrl(){tryClipboardUrl(true,true)}
function autoClipboardUrl(){if(playerActive()&&!$('#url').value.trim())tryClipboardUrl(false,false)}
function schedulePreview(){clearTimeout(previewTimer);previewTimer=setTimeout(previewUrl,500)}
function drawPreview(r){let box=$('#player-preview');if(!box)return;if(!r||!r.ok){box.classList.remove('on');box.innerHTML='';if(r&&r.error)msg(r.error,'err');return}let img=r.thumbnail?'<img src="'+esc(r.thumbnail)+'" alt="">':'';let dur=r.duration?fmt(r.duration):'';let meta=(r.type||'media')+(dur?' · '+dur:'')+(r.uploader?' · '+esc(r.uploader):'');box.innerHTML=img+'<div><div id="player-preview-title">'+esc(r.title||'Preview')+'</div><div class="media-meta">'+meta+'</div></div>';box.classList.add('on')}
async function previewUrl(){let u=$('#url').value.trim();let seq=++previewSeq;if(!looksMediaUrl(u)){drawPreview(null);return}let r=await api('/media/preview?url='+encodeURIComponent(u));if(seq===previewSeq)drawPreview(r)}
async function play(){let u=$('#url').value.trim(),q=$('#qual').value;if(!u){msg('Enter URL','err');return}let mr=await api('/mpv/memory?url='+encodeURIComponent(u));let mem=mr&&mr.memory;let resume=false;if(mem&&mem.position!==null&&mem.position>0&&mem.duration&&(mem.duration-mem.position)>30&&mem.position<mem.duration*.95){let pos=mem.position;let hrs=Math.floor(pos/3600);let mins=Math.floor((pos%3600)/60);let secs=Math.floor(pos%60);let tstr;if(hrs>0){tstr=hrs+':'+(mins<10?'0':'')+mins+':'+(secs<10?'0':'')+secs}else{tstr=mins+':'+(secs<10?'0':'')+secs}if(confirm('Resume from '+tstr+'?')){resume=true}else{await api('/mpv/memory/clear?url='+encodeURIComponent(u));}}let r=await api('/mpv/play?url='+encodeURIComponent(u)+'&q='+q+'&resume='+(resume?'1':'0'));if(r.error)msg(r.error,'err');else msg('Playing: '+(r.meta&&r.meta.title||r.q),'ok');setTimeout(st,1500)}
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
function getCookie(name){let prefix=encodeURIComponent(name)+'=';let item=document.cookie.split(';').map(x=>x.trim()).find(x=>x.startsWith(prefix));return item?decodeURIComponent(item.slice(prefix.length)):''}
function setCookie(name,value){document.cookie=encodeURIComponent(name)+'='+encodeURIComponent(value)+'; path=/; max-age=31536000; SameSite=Lax'}
const LANG_KEY='rpidash-lang'
const I18N={cz:{player:'Přehrávač',apps:'Aplikace',cec:'CEC',kodi:'Kodi',audio:'Audio',devices:'Zařízení',terminal:'Terminál',status:'Stav',quick:'Rychlé',ageCookies:'Věk / cookies',cookieStatus:'Stav cookies',ageCheck:'Kontrola věku',play:'Přehrát',pasteClipboard:'Vložit schránku',openHttps:'Otevřít HTTPS',httpFallbackBanner:'HTTP fallback je aktivní. Pro vložení ze schránky použij zabezpečenou verzi.',secureClipboardEnabled:'Zabezpečená verze: clipboard je povolený po schválení oprávnění prohlížeče.',refresh:'Obnovit',connect:'Připojit',disconnect:'Odpojit',saveApply:'Uložit + použít',inputUrl:'YouTube nebo přímá URL...',audioDelay:'Audio delay (ms):',playerDesc:'Přehrávání YouTube/mpv a diagnostika cookies.',appsDesc:'Spuštění aplikací a návrat do dashboardu.',cecPower:'Napájení',cecBridge:'Remote→MPV Bridge',cecNav:'Navigace',cecVol:'Hlasitost',cecInput:'Vstup',cecDevices:'Zařízení',kodiTitle:'Kodi JSON-RPC launcher',kodiDesc:'Legacy cesta pro odeslání URL do lokálního Kodi na 127.0.0.1:9090 přes Player.Open. Smysl má jen pokud Kodi skutečně běží jako renderer/přehrávač; běžné YouTube/mpv přehrávání používá kartu Player.',audioTitle:'Audio & Media',audioDesc:'Hlavní směrování zvuku a mixer. Párování reproduktorů je v Zařízeních; směrování výstupu je zde.',outputSinks:'Výstupní zařízení',inputSources:'Vstupní zdroje',mixer:'Mixér — aktivní streamy',audioRouting:'Směrování zvuku',dlnaLatency:'Kompenzace DLNA zpoždění',ytAge:'YouTube věk / cookies',ytAgeDesc:'Kontrola čerstvosti cookies bez vyzrazení hodnot. Použij, když age-restricted video nejde přehrát.',diagnostics:'Diagnostika',devicesTitle:'Zařízení',devicesDesc:'Páruj a připojuj hardware zde. Směrování reproduktoru a hlasitost zůstávají v Audio.',btPair:'Párování Bluetooth',wifiConfig:'Wi‑Fi konfigurace',roles:'Doporučené role zařízení',rolesDesc:'• Reproduktory/sluchátka/soundbary: páruj/připoj/důvěřuj zde, pak zvol routování v Audio.<br>• Xbox ovladače/gamepady: páruj/připoj/důvěřuj zde pro vstupní použití; žádné audio routování se neprovádí.<br>• Remote mikrofon a USB Alexa input jsou zobrazeny v Audio jako zdroje.<br>• Budoucí doplnění: HDMI-CEC inventář, Tailscale stav, health USB/storage zařízení.',termConnect:'Připojit',termDisconnect:'Odpojit',scan:'Skenovat',pair:'Párovat',trust:'Důvěřovat',remove:'Odebrat',found:'Nalezeno',paired:'spárováno',connected:'Připojeno',disconnected:'Odpojeno',playing:'Přehrávám',paused:'Pozastaveno',stopped:'Zastaveno',language:'Jazyk',clickScan:'Klikni na Skenovat',clickScanRefresh:'Klikni na Skenovat nebo Obnovit',clickCookieStatus:'Klikni na Stav cookies',appsLaunch:'Spustit aplikaci',appsReturn:'Návrat do Dashboardu',appsReturnDesc:'• <b>Ctrl+C</b> — ukončí většinu aplikací<br>• <b>Ctrl+Q</b> — ukončí Steam Link<br>• <b>tlačítko ZASTAVIT</b> — vynutí návrat<br>• Aplikace běží přímo na TV, dashboard se automaticky vrátí po ukončení',cecBridgeDesc:'Play/Pause, Stop, Seek, Vol via TV remote',ssid:'SSID',password:'Heslo',tipPlayerInput:'Vlož YouTube URL nebo přímý odkaz na video/audio.',tipAgeCheck:'Zadej YouTube URL pro kontrolu věkového ověření.',tipCecScan:'Prohledá CEC sběrnici a zobrazí HDMI zařízení.',tipCecBridge:'Přeposílá tlačítka TV ovladače na mpv.',tipAudioBt:'Přepne výstup na Bluetooth soundbar.',tipAudioHdmi:'Přepne výstup na HDMI.',tipAudioDlna:'Přepne výstup na DLNA zařízení.',tipDlnaLatency:'Nastav zpoždění zvuku při DLNA přehrávání.',tipBtScan:'Skenuje okolní Bluetooth zařízení.',tipWifiScan:'Skenuje dostupné Wi-Fi sítě.',tipWifiConnect:'Připojí RPi ke zvolené Wi-Fi. Heslo zůstává jen v prohlížeči.',tipKodiUrl:'URL adresa odeslaná do Kodi přes JSON-RPC.',tipMpvQ:'Kvalita přehrávání; vyšší rozlišení víc zatěžuje RPi.',feedbackBtn:'💬 Zpětná vazba',feedbackTitle:'💬 Odeslat zpětnou vazbu',feedbackTypeLabel:'Typ:',feedbackBug:'Nahlásit chybu',feedbackFeature:'Návrh na vylepšení',feedbackDescLabel:'Popis:',feedbackSubmit:'Odeslat',feedbackPlaceholder:'Zde popište chybu nebo nápad...',feedbackRequired:'Popis je povinný.',feedbackSending:'Odesílám zpětnou vazbu...',feedbackSuccess:'Zpětná vazba byla uložena! Soubor:',feedbackFailed:'Chyba při odesílání zpětné vazby.',ssidRequired:'Název sítě SSID je povinný.',wifiConnected:'Wi‑Fi připojena.',wifiFailed:'Připojení k Wi‑Fi selhalo.',wifiScanning:'Skenování Wi‑Fi...',wifiScanDone:'Skenování Wi‑Fi dokončeno.',wifiScanFailed:'Skenování Wi‑Fi selhalo.',ytUrlRequired:'Zadejte YouTube URL.',ytChecking:'Ověřování věku a cookies...',ytExtractable:'Video lze bez problému přehrát.',ytFailed:'Ověření věku selhalo.',launching:'Spouštím',failed:'selhalo',stopping:'Zastavování...',termReady:'Terminál připraven.',connectionError:'Chyba připojení.',appsMpv:'🎬 MPV Přehrávač',appsStopReturn:'⏹ ZASTAVIT & VRÁTIT SE',hwStatsTitle:'HW Statistiky & Zátěž',hwUpdateBtn:'Aktualizovat',hwLiveBtn:'Živé sledování',hwLoading:'Načítám HW statistiky...',sysLoading:'Načítám parametry procesů...',restartTitle:'Restart Systému',restartMpv:'Restart mpv',restartDashboard:'Restart Dashboardu',restartRpi:'Restart RPi',taDefault:'Výchozí výstup:',taRaw:'Surová JSON data',clickRefresh:'Klikni Obnovit',wifiUse:'Použít',wifiNone:'Žádné sítě nenalezeny'},en:{player:'Player',apps:'Apps',cec:'CEC',kodi:'Kodi',audio:'Audio',devices:'Devices',terminal:'Terminal',status:'Status',quick:'Quick',ageCookies:'Age / cookies',cookieStatus:'Cookie status',ageCheck:'Age check',play:'Play',pasteClipboard:'Paste clipboard',openHttps:'Open HTTPS',httpFallbackBanner:'HTTP fallback is active. Use the secure version for clipboard paste.',secureClipboardEnabled:'Secure version: clipboard is enabled after browser permission.',refresh:'Refresh',connect:'Connect',disconnect:'Disconnect',saveApply:'Save + apply',inputUrl:'YouTube or direct URL...',audioDelay:'Audio delay (ms):',playerDesc:'YouTube/mpv playback and cookie diagnostics.',appsDesc:'Launch apps and return to the dashboard.',cecPower:'Power',cecBridge:'Remote→MPV Bridge',cecNav:'Navigation',cecVol:'Volume',cecInput:'Input',cecDevices:'Devices',kodiTitle:'Kodi JSON-RPC launcher',kodiDesc:'Legacy route for sending a URL to a local Kodi instance on 127.0.0.1:9090 via Player.Open. It is useful only if Kodi is installed/running as a renderer; normal YouTube/mpv playback uses the Player tab.',audioTitle:'Audio & Media',audioDesc:'Primary audio routing and mixer. Speaker pairing lives in Devices; output routing lives here.',outputSinks:'Output Sinks',inputSources:'Input Sources',mixer:'Mixer — Active Streams',audioRouting:'Audio Routing',dlnaLatency:'DLNA Latency Compensation',ytAge:'YouTube Age / Cookies',ytAgeDesc:'Checks cookie freshness without exposing cookie values. Use this when age-restricted videos fail.',diagnostics:'Diagnostics',devicesTitle:'Devices',devicesDesc:'Pair and connect hardware here. Speaker output routing and volume remain in Audio.',btPair:'Bluetooth Pairing',wifiConfig:'Wi‑Fi Configuration',roles:'Suggested Device Roles',rolesDesc:'• Speakers/headphones/soundbars: pair/connect/trust here, then choose routing in Audio.<br>• Xbox controllers/gamepads: pair/connect/trust here for input use; no audio routing is applied.<br>• Remote microphone and USB Alexa input are shown in Audio as sources.<br>• Future additions: HDMI-CEC device inventory, Tailscale status, storage/USB device health.',termConnect:'Connect',termDisconnect:'Disconnect',scan:'Scan',pair:'Pair',trust:'Trust',remove:'Remove',found:'Found',paired:'paired',connected:'Connected',disconnected:'Disconnected',playing:'Playing',paused:'Paused',stopped:'Stopped',language:'Language',clickScan:'Click Scan',clickScanRefresh:'Click Scan or Refresh',clickCookieStatus:'Click Cookie status',appsLaunch:'Launch app',appsReturn:'Back to Dashboard',appsReturnDesc:'• <b>Ctrl+C</b> — closes most applications<br>• <b>Ctrl+Q</b> — closes Steam Link<br>• <b>STOP button</b> — forces a return<br>• Apps run directly on the TV and the dashboard returns automatically after exit',cecBridgeDesc:'Play/Pause, Stop, Seek, Volume via TV remote',ssid:'SSID',password:'Password',tipPlayerInput:'Paste a YouTube URL or direct video/audio link.',tipAgeCheck:'Enter a YouTube URL to check age/cookie status.',tipCecScan:'Scan the CEC bus and list HDMI devices.',tipCecBridge:'Forward TV remote buttons to mpv.',tipAudioBt:'Switch audio output to Bluetooth soundbar.',tipAudioHdmi:'Switch audio output to HDMI.',tipAudioDlna:'Switch audio output to a DLNA device.',tipDlnaLatency:'Set audio delay offset for DLNA playback.',tipBtScan:'Scan nearby Bluetooth devices.',tipWifiScan:'Scan available Wi-Fi networks.',tipWifiConnect:'Connect to a Wi-Fi network. Password stays only in your browser.',tipKodiUrl:'URL address to send to Kodi via JSON-RPC.',tipMpvQ:'Playback quality; higher resolution uses more RPi resources.',feedbackBtn:'💬 Feedback',feedbackTitle:'💬 Submit Feedback',feedbackTypeLabel:'Type:',feedbackBug:'Bug Report',feedbackFeature:'Feature Request',feedbackDescLabel:'Description:',feedbackSubmit:'Submit',feedbackPlaceholder:'Please describe the issue or your feature request...',feedbackRequired:'Description is required.',feedbackSending:'Submitting feedback...',feedbackSuccess:'Feedback submitted! File:',feedbackFailed:'Failed to submit feedback.',ssidRequired:'SSID required.',wifiConnected:'Wi-Fi connected.',wifiFailed:'Wi-Fi connection failed.',wifiScanning:'Scanning Wi-Fi...',wifiScanDone:'Wi-Fi scan done.',wifiScanFailed:'Wi-Fi scan failed.',ytUrlRequired:'Enter YouTube URL.',ytChecking:'Checking YouTube age/cookies...',ytExtractable:'Video is extractable.',ytFailed:'Age/cookie check failed.',launching:'Launching',failed:'failed',stopping:'Stopping...',termReady:'Terminal ready.',connectionError:'Connection error.',appsMpv:'🎬 MPV Player',appsStopReturn:'⏹ STOP & RETURN',hwStatsTitle:'HW Stats & CPU Masks',hwUpdateBtn:'Update',hwLiveBtn:'Live monitoring',hwLoading:'Loading HW stats...',sysLoading:'Loading CPU masks...',restartTitle:'Restart Actions',restartMpv:'Restart mpv',restartDashboard:'Restart Dashboard',restartRpi:'Restart RPi',taDefault:'Default sink:',taRaw:'Raw technical JSON',clickRefresh:'Click Refresh',wifiUse:'Use',wifiNone:'No networks found'}}

const HELPERS={
cz:{
sectionPlayer:'Přehrávač: vlož YouTube nebo přímou URL, vyber kvalitu a spusť mpv. Stav ukazuje titul, čas, pauzu, hlasitost a kvalitu. Ovládání seek/volume funguje i přes klávesy a remote bridge.',
sectionQuick:'Rychlé testovací odkazy pro ověření, že mpv/youtube pipeline funguje. Nepoužívej pro produkční diagnostiku, jen jako rychlý smoke test.',
sectionAgeCookies:'Ověření věku a cookies: 1) vlož problematické YouTube URL do pole v této sekci; 2) klikni Stav cookies a zkontroluj, že yt-cookies.txt existuje a není prázdný; 3) klikni Kontrola věku; 4) pokud je ok=true, yt-dlp video umí extrahovat s aktuálními cookies; 5) pokud kontrola selže na age/cookies, obnov cookies z BrowserOS/CDP na Milhy-PC a test zopakuj. Hodnoty cookies se nikdy nezobrazují, jen metadata/diagnostika.',
sectionApps:'Aplikace spouští externí režimy přes mode-switcher API. Po spuštění aplikace běží přímo na TV; návrat řeš tlačítkem ZASTAVIT nebo klávesami uvedenými níže.',
sectionAppsReturn:'Návod k návratu z aplikací. Steam Link typicky ukončí Ctrl+Q, ostatní Ctrl+C; tlačítko ZASTAVIT vynutí návrat do dashboardu.',
sectionCecPower:'CEC napájení a scan HDMI sběrnice. Scan jen vypíše zařízení, On/Off posílá CEC příkaz TV.',
sectionCecBridge:'Remote→MPV Bridge přeposílá tlačítka TV ovladače do mpv: play/pause, stop, seek a volume. Zapínej jen když chceš ovládat aktuální mpv přehrávání TV ovladačem.',
sectionCecNav:'CEC navigační tlačítka posílají jednotlivé keypress příkazy do TV/CEC zařízení.',
sectionCecVol:'CEC hlasitost posílá volume/mute příkazy přes HDMI-CEC, nezávisle na mpv volume.',
sectionCecInput:'Přepnutí HDMI vstupu přes CEC active-source. Funkčnost závisí na TV.',
sectionCecDevices:'Výstup posledního CEC scanu. Pokud je prázdný, TV/adapter nemusí odpovídat.',
sectionAudio:'Audio & Media je hlavní místo pro routování zvuku. Výstup zvolíš BT/HDMI/DLNA, hlasitost řeší slidery, párování zařízení je v záložce Zařízení.',
sectionOutputSinks:'Výstupní zařízení: HDMI, BT soundbar, DLNA a případně USB output. CONNECTED znamená výchozí aktivní sink.',
sectionInputSources:'Vstupní zdroje: USB Alexa input, remote mic a další capture zařízení. Tady se jen zobrazují, routování je níže.',
sectionMixer:'Mixer ukazuje aktivní audio streamy a kam jsou routované. Keepalive streamy jsou schované, aby nerušily diagnostiku.',
sectionAudioRouting:'Směrování zvuku pro složitější trasy, např. Alexa AUX/USB input → Bluetooth soundbar přes PipeWire loopback.',
sectionDlnaLatency:'Kompenzace DLNA zpoždění nastavuje mpv audio-delay v milisekundách. Kladná hodnota zpozdí audio, záporná ho posune dopředu.',
sectionDiagnostics:'Lidské shrnutí a raw JSON pro debug audio stavu. Raw JSON používej při reportu problémů.',
sectionDevices:'Zařízení slouží pro párování/připojení hardwaru. Speaker se zde páruje, ale audio výstup se volí v Audio.',
sectionBluetooth:'Bluetooth pairing: sken najde okolní zařízení, Pair spáruje, Trust uloží důvěru, Connect připojí. Gamepady se nepoužívají jako audio.',
sectionWifi:'Wi‑Fi konfigurace přes nmcli. Heslo zůstává v prohlížeči a posílá se jen na lokální endpoint pro připojení.',
sectionRoles:'Doporučené role vysvětlují, kde spravovat reproduktory, ovladače, mikrofony a budoucí hardware.',
sectionTerminal:'Web terminál se připojuje přes WebSocket na tmux session RPi. Používej na rychlou diagnostiku bez SSH.',
sectionKodi:'Kodi je legacy JSON-RPC launcher na 127.0.0.1:9090. Normální YouTube/mpv přehrávání používej přes Player; Kodi má smysl jen pokud lokální Kodi opravdu běží.'
},
en:{
sectionPlayer:'Player: paste a YouTube or direct URL, choose quality, and start mpv. Status shows title, time, pause state, volume, and quality. Seek/volume also work via keyboard and remote bridge.',
sectionQuick:'Quick test links for checking that the mpv/youtube pipeline works. Use as a smoke test only, not as production diagnostics.',
sectionAgeCookies:'Age and cookies verification: 1) paste the problematic YouTube URL into this section; 2) click Cookie status and verify yt-cookies.txt exists and is not empty; 3) click Age check; 4) if ok=true, yt-dlp can extract the video with current cookies; 5) if it fails on age/cookies, refresh cookies from BrowserOS/CDP on Milhy-PC and repeat. Cookie values are never shown, only metadata/diagnostics.',
sectionApps:'Apps launch external modes through the mode-switcher API. After launch, the app runs directly on the TV; return with STOP or the shortcuts listed below.',
sectionAppsReturn:'Return instructions for apps. Steam Link usually exits with Ctrl+Q, most others with Ctrl+C; STOP forces a return to dashboard.',
sectionCecPower:'CEC power and HDMI bus scan. Scan only lists devices; On/Off sends CEC commands to the TV.',
sectionCecBridge:'Remote→MPV Bridge forwards TV remote buttons to mpv: play/pause, stop, seek, and volume. Enable it only when you want to control current mpv playback via TV remote.',
sectionCecNav:'CEC navigation buttons send individual keypress commands to the TV/CEC device.',
sectionCecVol:'CEC volume sends volume/mute commands over HDMI-CEC, independent of mpv volume.',
sectionCecInput:'HDMI input switching via CEC active-source. Support depends on the TV.',
sectionCecDevices:'Output of the last CEC scan. Empty output means the TV/adapter may not respond.',
sectionAudio:'Audio & Media is the main audio routing page. Choose BT/HDMI/DLNA output here, adjust volume with sliders, and pair devices in Devices.',
sectionOutputSinks:'Output devices: HDMI, BT soundbar, DLNA, and optional USB output. CONNECTED marks the current default sink.',
sectionInputSources:'Input sources: USB Alexa input, remote mic, and other capture devices. They are shown here; routing is below.',
sectionMixer:'Mixer shows active audio streams and their target sinks. Keepalive streams are hidden to keep diagnostics readable.',
sectionAudioRouting:'Advanced audio routes, e.g. Alexa AUX/USB input → Bluetooth soundbar via PipeWire loopback.',
sectionDlnaLatency:'DLNA latency compensation sets mpv audio-delay in milliseconds. Positive delays audio, negative advances it.',
sectionDiagnostics:'Human summary and raw JSON for audio debugging. Use raw JSON when reporting issues.',
sectionDevices:'Devices is for pairing and connecting hardware. Pair speakers here, but choose audio output in Audio.',
sectionBluetooth:'Bluetooth pairing: scan finds nearby devices, Pair pairs, Trust stores trust, Connect connects. Gamepads are not used as audio.',
sectionWifi:'Wi‑Fi configuration through nmcli. Password stays in the browser and is sent only to the local connect endpoint.',
sectionRoles:'Suggested roles explain where to manage speakers, controllers, microphones, and future hardware.',
sectionTerminal:'Web terminal connects through WebSocket to tmux session RPi. Use it for quick diagnostics without SSH.',
sectionKodi:'Kodi is the legacy JSON-RPC launcher on 127.0.0.1:9090. Use Player for normal YouTube/mpv playback; Kodi matters only if local Kodi is actually running.'
}}
function helperText(k){return (HELPERS[LANG]&&HELPERS[LANG][k])||((HELPERS.cz&&HELPERS.cz[k])||L(k))}

let LANG=(localStorage.getItem(LANG_KEY)||'cz').toLowerCase()==='en'?'en':'cz'
function L(k){return (I18N[LANG]&&I18N[LANG][k])||((I18N.cz&&I18N.cz[k])||k)}
function ariaText(k,txt){if(txt!==k)return txt;let m={cz:{pause:'Pozastavit',stop:'Zastavit',rewind10:'Zpět 10 sekund',forward10:'Vpřed 10 sekund',volumedown:'Snížit hlasitost',volumeup:'Zvýšit hlasitost',mute:'Ztlumit'},en:{pause:'Pause',stop:'Stop',rewind10:'Rewind 10 seconds',forward10:'Forward 10 seconds',volumedown:'Volume down',volumeup:'Volume up',mute:'Mute'}};return (m[LANG]&&m[LANG][k])||((m.en&&m.en[k])||txt)}
function formatMsg(k,vars){let s=L(k);Object.entries(vars||{}).forEach(([key,val])=>{s=s.replaceAll('{'+key+'}',String(val))});return s}
function tip(el,key){let w=document.createElement('span');w.className='tip-wrap';let b=document.createElement('button');b.className='info-btn';b.textContent='i';b.setAttribute('aria-label','Help');b.setAttribute('type','button');let box=document.createElement('div');box.className='tip-box';box.dataset.tipBox=key;box.textContent=helperText(key);b.addEventListener('click',function(e){e.stopPropagation();document.querySelectorAll('.tip-box.show').forEach(x=>{if(x!==box)x.classList.remove('show')});box.classList.toggle('show')});w.appendChild(b);w.appendChild(box);el.insertAdjacentElement('afterend',w)}
function addTips(){document.querySelectorAll('[data-tip]').forEach(el=>{if(!el.nextElementSibling||!el.nextElementSibling.classList.contains('tip-wrap'))tip(el,el.dataset.tip)})}
function setLang(code){LANG=(code||'cz').toLowerCase()==='en'?'en':'cz';try{localStorage.setItem(LANG_KEY,LANG)}catch{};applyLang()}
function applyLang(){document.documentElement.lang=LANG==='en'?'en':'cs';document.querySelectorAll('[data-i18n]').forEach(el=>{let key=el.dataset.i18n;let txt=L(key);if(el.dataset.i18nAttr==='placeholder'){el.placeholder=txt;return}if(el.dataset.i18nAttr==='title'){el.title=txt;return}if(el.dataset.i18nAttr==='aria-label'){el.setAttribute('aria-label',ariaText(key,txt));return}let icon=el.dataset.icon||'';el.innerHTML=(icon?icon+' ':'')+txt});document.querySelectorAll('[data-tip]').forEach(el=>{if(el.nextElementSibling&&el.nextElementSibling.classList.contains('tip-wrap')){let box=el.nextElementSibling.querySelector('.tip-box');if(box)box.textContent=helperText(el.dataset.tip)}});document.querySelectorAll('[data-lang-btn]').forEach(btn=>btn.classList.toggle('active',btn.dataset.langBtn===LANG));let ls=$('#lang-status');if(ls)ls.textContent=LANG==='en'?'EN':'CZ';updateSecurityBanner()}
document.addEventListener('click',()=>{document.querySelectorAll('.tip-box.show').forEach(x=>x.classList.remove('show'));autoClipboardUrl()})
window.addEventListener('focus',()=>setTimeout(autoClipboardUrl,120))
document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(autoClipboardUrl,120)})
function terminalActive(){let p=$('#p-terminal');let ae=document.activeElement;let t=document.getElementById('terminal');return !!((p&&p.classList.contains('active'))||(ae&&ae.closest&&(ae.closest('#terminal')||ae.closest('.xterm')||ae.classList.contains('xterm-helper-textarea')))||(t&&t.contains(ae)))}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.isContentEditable||terminalActive())return;switch(e.key){case'ArrowLeft':e.preventDefault();seek(-10);msg('⏪ -10s','info');break;case'ArrowRight':e.preventDefault();seek(10);msg('⏩ +10s','info');break;case'ArrowUp':e.preventDefault();vol(5);msg('🔊 +5%','info');break;case'ArrowDown':e.preventDefault();vol(-5);msg('🔉 -5%','info');break;case' ':return;case'MediaPlayPause':e.preventDefault();pause();msg('⏯ Play/Pause','info');break;case'MediaTrackNext':e.preventDefault();seek(30);msg('⏩ +30s','info');break;case'MediaTrackPrevious':e.preventDefault();seek(-30);msg('⏪ -30s','info');break;case'VolumeUp':e.preventDefault();vol(5);msg('🔊 +5%','info');break;case'VolumeDown':e.preventDefault();vol(-5);msg('🔉 -5%','info');break;case'AudioVolumeMute':e.preventDefault();api('/mpv/vol?d=-100');msg('🔇 Mute','info');break;case'f':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.25).toFixed(1));msg('⏪ 25%','info');break;case'g':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.5).toFixed(1));msg('⏩ 50%','info');break;case'h':e.preventDefault();api('/mpv/seekabs?pos='+(lastDur*0.75).toFixed(1));msg('⏩ 75%','info');break}})
function qu(u){$('#url').value=u;play()}
async function cec(c){msg('CEC: '+c,'info');let r=await api('/cec/send?c='+encodeURIComponent(c));msg(r.ok?'OK: '+c:(r.err||'fail'),r.ok?'ok':'err')}
async function cecKey(k){let r=await api('/cec/key?k='+encodeURIComponent(k));msg(r.ok?'OK: '+k:'fail',r.ok?'ok':'err')}
async function cecIn(n){let r=await api('/cec/in?n='+n);msg('HDMI '+n+': '+(r.ok?'ok':r.err||'?'),r.ok?'ok':'err')}
async function cecScan(){msg('Scanning CEC...','info');let r=await api('/cec/scan');$('#cdev').innerHTML='<pre>'+esc(r.out||r.err||'none')+'</pre>';msg(r.out?'Scan done':'No devices',r.out?'ok':'err')}

let hwLiveTimer=null;
function toggleHwLive(){
    let b=$('#hw-live-btn');
    if(hwLiveTimer){clearInterval(hwLiveTimer);hwLiveTimer=null;if(b)b.textContent='▶ Live monitoring';msg('Live monitoring off','info');return}
    loadHwStats();loadSysStatus();
    hwLiveTimer=setInterval(()=>{if($('#p-terminal')&&$('#p-terminal').classList.contains('active')){loadHwStats();loadSysStatus()}},3000);
    if(b)b.textContent='⏸ Live monitoring';msg('Live monitoring on','ok');
}
async function loadHwStats(){
    let r=await api('/system/hw-stats');
    if(r.error){$('#hw-stats').textContent='Chyba: '+r.error;return}
    let cpu=(r.cpu||[]).map((v,i)=>'Core'+i+' '+v.toFixed(0)+'%').join('  ');
    let temp=r.temp_c===null?'?':r.temp_c.toFixed(1)+'°C';
    let freq=(r.freq_mhz||[]).map((v,i)=>'C'+i+' '+v+'MHz').join('  ');
    let gpu=r.gpu||{};let gpuLine='GPU: core '+(gpu.core_mhz??'?')+'MHz, temp '+(gpu.temp_c??'?')+'°C';
    let diskAvail=r.disk.avail_gb!==undefined?' avail '+r.disk.avail_gb+' GB':'';
    $('#hw-stats').textContent='CPU: '+cpu+'\nLoad: '+r.loadavg.join(' ')+'\nTemp: '+temp+'\nFreq: '+freq+'\n'+gpuLine+'\nRAM: '+r.ram.used_mb+'/'+r.ram.total_mb+' MB ('+r.ram.percent+'%)\nDisk: '+r.disk.used_gb+'/'+r.disk.total_gb+' GB ('+r.disk.percent+'%)'+diskAvail+'\nUptime: '+r.uptime;
}

async function loadSysStatus(){
    let r=await api('/system/status');
    if(r.error){$('#sys-status').textContent='Chyba: '+r.error;return}
    let html='CPU Mask / Core Assignments:<br>';
    html+='mpv: mask '+r.mpv.mask+' (cores: '+r.mpv.cores+')<br>';
    html+='dashboard: mask '+r.dashboard.mask+' (cores: '+r.dashboard.cores+')<br>';
    html+='keys2mpv: mask '+r.keys2mpv.mask+' (cores: '+r.keys2mpv.cores+')<br>';
    html+='webserver: mask '+r.webserver.mask+' (cores: '+r.webserver.cores+')<br>';
    html+='pipewire: mask '+r.pipewire.mask+' (cores: '+r.pipewire.cores+')<br>';
    html+='wireplumber: mask '+r.wireplumber.mask+' (cores: '+r.wireplumber.cores+')<br>';
    $('#sys-status').innerHTML=html;
}

async function restartMpv(){
    if(!confirm('Opravdu restartovat mpv?')) return;
    let r=await api('/system/restart-mpv');
    msg(r.out||'mpv stopped','ok');
}

async function restartDashboard(){
    if(!confirm('Opravdu restartovat Dashboard?')) return;
    let r=await api('/system/restart-dashboard');
    msg(r.out||'Dashboard restarting...','ok');
}

async function restartRpi(){
    if(!confirm(L('confirmReboot'))) return;
    let r=await api('/system/restart-rpi');
    msg(r.out||L('rebooting'),'ok');
}
async function cecBr(){let s=await api('/cec/br/st');if(s.on){await api('/cec/br/stop');msg(L('bridgeOff'),'info')}else{let r=await api('/cec/br/start');msg(r.ok?L('bridgeOn'):L('failed'),r.ok?'ok':'err')}updBr()}
async function updBr(){let r=await api('/cec/br/st'),b=$('#brb');if(r.on){b.textContent='⏹ '+L('cecStop');b.className='on';$('#brs').textContent=L('connected')+' — remote→mpv'}else{b.textContent='▶ '+L('cecStart');b.className='';$('#brs').textContent=L('disconnected')}}
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
function meter(v,kind,name){let n=(v==null?0:v);if(!kind||!name)return '<div class="meter"><span style="width:'+n+'%"></span></div><div class="media-meta">Volume: '+(v==null?'—':v+'%')+'</div>';let id='vol-'+kind+'-'+esc(name).replace(/[^a-zA-Z0-9]/g,'_').substring(0,30);return '<div style="display:flex;align-items:center;gap:.4rem;margin:.2rem 0"><input type="range" id="'+id+'" min="0" max="150" value="'+n+'" step="1" style="flex:1;height:6px;accent-color:#58a6ff;cursor:pointer" oninput="this.nextElementSibling.textContent=this.value+\'%\'; taSetVolDebounced(\''+kind+'\',\''+jsarg(name)+'\',this.value)" onchange="taSetVol(\''+kind+'\',\''+jsarg(name)+'\',this.value)" ontouchstart="event.stopPropagation()"><span style="min-width:36px;font-size:.8em;text-align:right">'+(v==null?'—':v+'%')+'</span><button onclick="taMute(\''+kind+'\',\''+jsarg(name)+'\')" style="font-size:.75em;padding:2px 6px" title="Mute/unmute">🔇</button></div>'}
function shortName(n){let s=(n||'').replace('alsa_output.platform-3f902000.hdmi.hdmi-stereo','HDMI').replace('alsa_output.platform-3f00b840.mailbox.stereo-fallback','Aux (3.5mm Jack)').replace('alsa_output.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-stereo','USB audio output').replace('alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback','Alexa USB input').replace('alsa_input.usb-XING_WEI_2.4G_USB_USB_Composite_Device-00.mono-fallback','Remote microphone');if(s.startsWith('bluez_output.'))s='BT Soundbar';if(s.includes('-uuid:'))s='DLNA ' + s.split('-uuid:')[0];return s}
function deviceCard(icon,title,d,isDefault){let ok=d&&d.present;let defBadge=isDefault?' <span class="badge ok" style="font-size:.6em">CONNECTED</span>':'';let kind=String((d&&d.type)||'').includes('input')?'source':'sink';return '<div class="media-card"><h4>'+icon+' '+title+' '+badge(ok,ok?'ONLINE':'MISSING')+defBadge+'</h4>'+meter(d&&d.volume,kind,d.name)+'<div class="media-meta">'+esc(shortName((d&&d.name)||'not detected'))+'<br>State: '+esc((d&&d.state)||'—')+'</div></div>'}
function btSoundbarCard(d,isDefault){let ok=d&&d.present,paired=d&&d.paired;let defBadge=isDefault?' <span class="badge ok" style="font-size:.6em">CONNECTED</span>':'';let h='<div class="media-card"><h4>🎧 BT Soundbar '+badge(ok,ok?'ONLINE':(paired?'PAIRED':'MISSING'))+defBadge+'</h4>'+meter(d&&d.volume,'sink',d.name);h+='<div class="media-meta">'+esc((d&&d.label)||'Samsung Soundbar')+'<br>MAC: '+esc((d&&d.mac)||'—')+'<br>Status: '+esc(ok?'Connected':'Paired, not connected')+'</div>';if(paired&&!ok)h+='<div class="row" style="margin-top:.45rem"><button onclick="taBtConnect(\''+jsarg(d.mac)+'\')">🔌 Connect Soundbar</button></div>';return h+'</div>'}
function dlnaOutputCard(d,selected,connected,keepalive){let ok=d&&d.present;let target=selected?('<br>Selected target: '+esc(selected.name||selected.location)):'<br>No target selected yet.';let connectBtns='';if(selected){if(connected){connectBtns='<button onclick="taDlnaDisconnect()" class="danger" style="font-size:.8em">⏹ Disconnect</button>'}else{connectBtns='<button onclick="taDlnaConnect()" style="font-size:.8em">🔌 Connect</button>'}}let kaBadge='';let hasDlnaKeepalive=keepalive&&d&&d.name&&keepalive.some(k=>k===d.name);if(hasDlnaKeepalive){kaBadge='<span class="badge ok" style="font-size:.65em;margin-left:.3rem">KEEPALIVE</span>'}let status=connected?badge(true,'CONNECTED'):(ok?badge(ok,'NOT CONNECTED'):badge(false,'NOT CONNECTED'));let h='<div class="media-card"><h4>📡 DLNA Output '+status+kaBadge+'</h4>'+meter(d&&d.volume,'sink',d.name)+'<div class="media-meta">Send RPi sound to a network DLNA speaker/TV.'+target+'</div><div class="row" style="margin-top:.4rem;gap:.4rem"><button onclick="taDlnaScan()">🔍 Scan renderers</button>'+connectBtns+'</div><div id="ta-dlna-out-list" class="media-meta" style="margin-top:.35rem">—</div></div>';return h}
function taHumanSummary(r){let d=r.devices||{},lat=r.latency||{},inputs=r.sink_inputs||[];let lines=[];lines.push('Default output: '+shortName(r.default_sink||'—'));lines.push('HDMI: '+(d.hdmi&&d.hdmi.present?'online, volume '+d.hdmi.volume+'%':'not available'));let ka=r.keepalive||[];lines.push('BT Soundbar: '+(d.bt_soundbar&&d.bt_soundbar.present?(ka.some(k=>k.startsWith('bluez'))?'connected + keepalive':'connected'):'paired but not connected'));lines.push('DLNA Output: '+((r.dlna_connected)?'connected + keepalive':((d.dlna_output&&d.dlna_output.present)?'active, not connected':'not connected')));if(lat.selected_dlna_renderer)lines.push('Selected DLNA target: '+(lat.selected_dlna_renderer.name||lat.selected_dlna_renderer.location));lines.push('Active streams: '+(inputs.length?inputs.map(i=>'playing through '+i.sink).join(', '):'none'));let dl=r.dlna_connected;let dly=lat.dlna_output_offset_ms||0;lines.push('DLNA delay offset: '+dly+' ms'+(dl&&dly?' (active, mpv audio-delay set)':''));return lines.map(x=>'<div>• '+esc(x)+'</div>').join('')}
async function taRefresh(){let r=await api('/audio/state');if(r.error){msg(r.error,'err');return}let d=r.devices||{};let sources=r.sources||[];let inputs=r.sink_inputs||[];let lat=r.latency||{};let outHtml='';let ds=r.default_sink||'';if(d.hdmi&&d.hdmi.present)outHtml+=deviceCard('📺','HDMI',d.hdmi,ds.includes('hdmi'));outHtml+=btSoundbarCard(d.bt_soundbar||{},ds.includes('bluez'));outHtml+=dlnaOutputCard(d.dlna_output||{},lat.selected_dlna_renderer,r.dlna_connected,r.keepalive);if(d.usb_output&&d.usb_output.present)outHtml+=deviceCard('🔌','USB Output',d.usb_output,ds.includes('usb'));$('#ta-sinks').innerHTML=outHtml;let srcHtml='';sources.forEach(s=>{let icon=s.type==='usb_input'?'🎙️':(s.type==='remote_input'?'🎮':(s.type==='dlna_input'?'📡':'🔊'));let title=s.type==='usb_input'?'Alexa USB Input':(s.type==='remote_input'?'Remote Mic':(s.type==='dlna_input'?'DLNA Input':'Other'));srcHtml+=deviceCard(icon,title,s)});$('#ta-sources').innerHTML=srcHtml;dlnaRendererRefresh();let mixerHtml='';let realInputs=inputs.filter(i=>!i.keepalive);
// Build pipe-map: source_name -> [{sink, format}]
let pipeMap={};
let activeSinks=new Set();
realInputs.forEach(i=>{
  let src=i.client&&parseInt(i.client)?('stream-'+i.id):'system';
  // Try to identify source by sink name
  let sn=i.sink||'';
  let sinkLabel=shortName(sn);
  if(!pipeMap[sinkLabel])pipeMap[sinkLabel]=[];
  pipeMap[sinkLabel].push({id:i.id,format:i.format||'unknown',raw:i});
  activeSinks.add(sinkLabel);
});

// Build output nodes from devices
let outNodes=[];
ds=r.default_sink||'';
if(d.hdmi&&d.hdmi.present)outNodes.push({icon:'📺',label:'HDMI',name:'HDMI',active:ds.includes('hdmi'),streams:pipeMap['HDMI']||[]});
outNodes.push({icon:'🔊',label:'BT Soundbar',name:'BT Soundbar',active:ds.includes('bluez'),streams:pipeMap['BT Soundbar']||[]});
outNodes.push({icon:'📡',label:'DLNA Output',name:'DLNA Output',active:ds.includes('WiiMu')||ds.includes('LinkPlayer'),streams:pipeMap['DLNA Output']||[]});
if(d.usb_output&&d.usb_output.present)outNodes.push({icon:'🔌',label:'USB Output',name:'USB Output',active:ds.includes('usb'),streams:pipeMap['USB Output']||[]});

// Build input nodes from sources
let inNodes=[];
// Ensure System/Media always exists if there's an internal stream that is not a physical input
let hasSystemStreams = realInputs.some(i => !sources.some(s => s.id === i.client));
if(hasSystemStreams || sources.length === 0) {
  inNodes.push({icon:'🎵',label:'System / Media',active:hasSystemStreams,system:true});
}

sources.forEach(s=>{
  let icon=s.type==='usb_input'?'🎙️':(s.type==='remote_input'?'🎮':(s.type==='dlna_input'?'📡':'🔊'));
  let title=s.type==='usb_input'?'Alexa USB':(s.type==='remote_input'?'Remote Mic':(s.type==='dlna_input'?'DLNA Input':'Other'));
  inNodes.push({icon:icon,label:title,active:s.state==='RUNNING',raw:s});
});

// Render as patchbay
mixerHtml+='<div style="display:flex;gap:1rem;align-items:stretch;min-height:200px">';

// Left column: inputs
mixerHtml+='<div style="flex:0 0 140px;display:flex;flex-direction:column;gap:.5rem;justify-content:center">';
mixerHtml+='<div style="font-size:.7rem;color:#8b949e;text-align:center;margin-bottom:.2rem">INPUTS</div>';
inNodes.forEach(n=>{
  let border=n.active?'border-color:#3fb950;box-shadow: 0 0 8px rgba(63,185,80,0.2)':'border-color:#30363d';
  let color=n.active?'color:#e6edf3':'color:#8b949e';
  mixerHtml+='<div style="border:1px solid '+border+';border-radius:6px;padding:.4rem .5rem;font-size:.8rem;display:flex;align-items:center;gap:.4rem;background:#161b22;transition:all 0.3s ease;'+color+'">';
  mixerHtml+=n.icon+' <span>'+esc(n.label)+'</span>'+(n.active?'<span style="color:#3fb950;margin-left:auto;font-size:0.6rem;animation:pulse 2s infinite">●</span>':'')+'</div>';
});
mixerHtml+='</div>';

// Middle: connections visual
mixerHtml+='<div style="flex:1;display:flex;align-items:center;justify-content:center;position:relative" aria-hidden="true">';
mixerHtml+='<svg style="width:100%;height:100%;position:absolute;top:0;left:0;overflow:visible" viewBox="0 0 200 200" preserveAspectRatio="none">';

// Defs for animated gradient
mixerHtml+='<defs><linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#238636" stop-opacity="0.3"/><stop offset="50%" stop-color="#3fb950" stop-opacity="1"/><stop offset="100%" stop-color="#238636" stop-opacity="0.3"/></linearGradient></defs>';
mixerHtml+='<style>@keyframes flow { to { stroke-dashoffset: -20; } } @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } } .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border-width: 0; }</style>';

let activeOutputs=outNodes.filter(o=>o.streams.length>0);
let totalOut=outNodes.length;
let totalIn=inNodes.length;

activeOutputs.forEach((o,oi)=>{
  let yOut=30+((oi+0.5)/totalOut)*140;

  o.streams.forEach(s=>{
    // Determine which input this stream belongs to
    let srcIdx = 0; // Default to first (System/Media)
    if (!inNodes[0].system) {
        // If System/Media is not there, we fallback
        srcIdx = inNodes.findIndex(n=>n.label.includes('Alexa')||n.label.includes('DLNA'));
        if(srcIdx<0)srcIdx=0;
    }

    // Try to be smarter - if it's the loopback module for Alexa, match the Alexa node
    if (s.raw && s.raw.client && s.raw.client !== 'system') {
        let matchedIdx = inNodes.findIndex(n => !n.system && n.raw && n.raw.id && s.raw.client.toString().includes(n.raw.id.toString()));
        if (matchedIdx >= 0) srcIdx = matchedIdx;
    }

    let yIn=30+((srcIdx+0.5)/totalIn)*140;

    // Smooth bezier curve
    let path = `M 10 ${yIn} C 100 ${yIn}, 100 ${yOut}, 190 ${yOut}`;

    // Background path
    mixerHtml+=`<path d="${path}" fill="none" stroke="#238636" stroke-width="3" opacity="0.2"/>`;
    // Animated overlay path
    mixerHtml+=`<path d="${path}" fill="none" stroke="url(#flowGrad)" stroke-width="3" stroke-dasharray="10,10" style="animation: flow 1s linear infinite" />`;
  });
});
mixerHtml+='</svg>';

// Screen reader only summary for accessibility
mixerHtml+='<div class="sr-only">Active audio routes: '+activeOutputs.map(o=>o.label+' has '+o.streams.length+' streams').join(', ')+'</div>';

mixerHtml+='<div style="position:relative;z-index:1;font-size:.75rem;color:#8b949e;text-align:center;background:#0d1117;padding:0.2rem 0.6rem;border-radius:10px;border:1px solid #30363d">'+activeOutputs.length+' active route'+(activeOutputs.length!==1?'s':'')+'</div>';
mixerHtml+='</div>';

// Right column: outputs
mixerHtml+='<div style="flex:0 0 160px;display:flex;flex-direction:column;gap:.5rem;justify-content:center">';
mixerHtml+='<div style="font-size:.7rem;color:#8b949e;text-align:center;margin-bottom:.2rem">OUTPUTS</div>';
outNodes.forEach(n=>{
  let streams=n.streams;
  let hasStreams=streams.length>0;
  let border=hasStreams?'border-color:#3fb950;box-shadow: 0 0 8px rgba(63,185,80,0.15)':(n.active?'border-color:#1f6feb':'border-color:#30363d');
  let bg=hasStreams?'background:#0d1117':'background:#161b22';
  let color=hasStreams?'color:#e6edf3':'color:#8b949e';
  mixerHtml+='<div style="border:1px solid '+border+';border-radius:6px;padding:.4rem .5rem;font-size:.8rem;transition:all 0.3s ease;'+bg+';'+color+'">';
  mixerHtml+='<div style="display:flex;align-items:center">'+n.icon+' <span style="margin-left:.4rem">'+esc(n.label)+'</span>'+(hasStreams?' <span style="color:#3fb950;margin-left:auto;font-size:.7rem;animation:pulse 2s infinite">▶ '+streams.length+'</span>':'')+'</div>';
  if(hasStreams){mixerHtml+='<div style="font-size:.65rem;color:#8b949e;margin-top:.3rem;border-top:1px dashed #30363d;padding-top:.2rem">'+streams.map(s=>esc(s.format)).join(', ')+'</div>'}
  mixerHtml+='</div>';
});
mixerHtml+='</div>';
mixerHtml+='</div>';
// Summary line
let totalStreams=realInputs.length;
mixerHtml+='<div style="font-size:.7rem;color:#8b949e;margin-top:.4rem;text-align:center">'+totalStreams+' active stream'+(totalStreams!==1?'s':'')+' · Default: '+esc(shortName(ds||'—'))+'</div>';
$('#ta-mixer').innerHTML=mixerHtml;routesRefresh();taMatrixRefresh();$('#ta-default').textContent=shortName(r.default_sink||'—');$('#ta-lat-dlna-offset').value=lat.dlna_output_offset_ms||0;$('#ta-summary').innerHTML=taHumanSummary(r);$('#ta-raw').textContent=JSON.stringify(r,null,2)}
async function taMatrixRefresh(){let r=await api('/audio/matrix');if(!r.nodes)return;let sources=Object.values(r.nodes).filter(n=>n.class.includes('Output/Audio')||n.class.includes('Audio/Source'));let sinks=Object.values(r.nodes).filter(n=>n.class.includes('Input/Audio')||n.class.includes('Audio/Sink'));let html='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:0.8rem;text-align:center;"><tr><th style="text-align:left;border-bottom:1px solid #30363d;padding:8px">Matrix (Src \\ Sink)</th>';sinks.forEach(s=>{html+='<th style="border-bottom:1px solid #30363d;padding:8px;" title="'+esc(s.desc)+'">'+esc(shortName(s.name))+'</th>'});html+='</tr>';sources.forEach(src=>{html+='<tr><td style="text-align:left;border-bottom:1px solid #30363d;padding:8px;"><b>'+esc(shortName(src.name))+'</b></td>';sinks.forEach(snk=>{let isLinked=r.links.some(l=>l[0]===src.id&&l[1]===snk.id);html+='<td style="border-bottom:1px solid #30363d;padding:8px"><input type="checkbox" '+(isLinked?'checked':'')+' onchange="taMatrixLink(\''+jsarg(src.name)+'\',\''+jsarg(snk.name)+'\',this.checked)" style="transform:scale(1.2);cursor:pointer;accent-color:#3fb950"></td>'});html+='</tr>'});html+='</table></div>';let el=$('#ta-matrix');if(el)el.innerHTML=html;}
async function taMatrixLink(out_n,in_n,checked){msg('Patching audio...','info');let r=await api('/audio/matrix/link?out='+encodeURIComponent(out_n)+'&in='+encodeURIComponent(in_n)+'&state='+(checked?'1':'0'));if(!r.ok)msg('Patch failed','err');else msg('Audio patched','ok');setTimeout(()=>{taRefresh()},500)}
async function taRoute(a){let r=await api('/audio/route/alexa-bt?action='+a);msg(r.ok?'Route '+a+' OK':(r.error||r.out||'Route failed'),r.ok?'ok':'err');setTimeout(taRefresh,800)}
async function dlnaRendererRefresh(){let r=await api('/dlna/renderer/status');let el=$('#ta-sources');if(!el)return;if(r.error)return;let h='<div class="media-card"><h4>📡 DLNA Renderer (RPi as target)</h4>';let statusBadge=r.running?badge(true,'RUNNING'):(r.installed?badge(false,'STOPPED'):badge(false,'NOT INSTALLED'));let readyBadge=r.ready?badge(true,'READY'):badge(false,'NOT READY');h+='<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">'+statusBadge+' '+readyBadge+'</div>';h+='<div class="media-meta">'+esc(r.name||'RPi Renderer');if(r.pid)h+=' · PID: '+r.pid;if(r.uptime){let m=Math.floor(r.uptime/60);h+=' · Uptime: '+m+'m '+((r.uptime%60))+'s'}h+=' · PipeWire: '+(r.pipewire?'✅':'❌')+'</div>';h+='<div class="row" style="margin-top:.4rem">';if(r.running){h+='<button onclick="dlnaRendererStop()" class="danger">⏹ Stop</button>'}else{let disabled=r.installed?'':' disabled title="Install gmediarender first"';h+='<button onclick="dlnaRendererStart()"'+disabled+'>▶ Start</button>'}h+='</div></div>';el.innerHTML+=h}
async function dlnaRendererStart(){msg('Starting DLNA renderer...','info');let r=await api('/dlna/renderer/start');msg(r.ok?'Renderer started':(r.error||'start failed'),r.ok?'ok':'err');setTimeout(()=>{taRefresh()},2000)}
async function dlnaRendererStop(){msg('Stopping DLNA renderer...','info');let r=await api('/dlna/renderer/stop');msg(r.ok?'Renderer stopped':(r.error||'stop failed'),r.ok?'ok':'err');setTimeout(()=>{taRefresh()},1500)}
async function routesRefresh(){let[alexa,_,dlnain,multi]=await Promise.all([api('/audio/route/alexa-bt?action=status'),api('/dlna/renderer/status').catch(()=>({})),api('/audio/route/dlna-input/status').catch(()=>({})),api('/audio/multi-output?action=status').catch(()=>({}))]);dlnain=dlnain||{};multi=multi||{};let el=$('#ta-routes');if(!el)return;let h='';let alexaOn=alexa.on;let alexaTarget=alexa.target||'?';let alexaDefault=alexa.default_sink||'?';
h+='<div class="media-card route-card '+(alexaOn?'on':'off')+'"><h4>🎙️ AUX In (Alexa) → follows primary</h4>';
h+='<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">'+badge(alexaOn,alexaOn?'ON':'OFF')+'</div>';
h+='<div class="media-meta">Source: USB C-Media mono · Target: '+esc(shortName(alexaTarget))+' · Default sink: '+esc(shortName(alexaDefault))+'</div>';
h+='<div class="row" style="margin-top:.45rem">';
if(alexaOn){h+='<button data-act="alexa-stop" class="danger">⏹ Stop</button> <button data-act="alexa-retarget">🔄 Retarget</button>'}else{h+='<button data-act="alexa-start">▶ Start</button>'}
h+='</div></div>';
h+='<div class="media-card route-card '+(dlnain.running?'on':'off')+'"><h4>📡 DLNA Input (RPi Renderer)</h4>';
h+='<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">'+badge(dlnain.running,dlnain.running?'ON':'OFF')+'</div>';
let mode=dlnain.mode||'follow';let modeLabel=mode==='follow'?'Follow primary':'Manual';let nextMode=mode==='follow'?'manual':'follow';
h+='<div class="media-meta">Mode: <button data-act="dlnain-mode" data-mode="'+nextMode+'" style="font-size:.75em;padding:.15rem .4rem">'+modeLabel+'</button>';
if(mode==='manual'&&dlnain.manual_sink)h+=' · Manual target: '+esc(shortName(dlnain.manual_sink));
if(dlnain.running&&dlnain.active_target)h+=' · Active: '+esc(shortName(dlnain.active_target));
h+='</div>';
if(mode==='manual'){h+='<div class="row" style="margin-top:.3rem;font-size:.78rem">';
let targets=[{n:'HDMI',s:'alsa_output.platform'},{n:'BT Soundbar',s:'bluez_output'},{n:'DLNA Output',s:'WiiMu'},{n:'USB Output',s:'alsa_output.usb'}];
targets.forEach(t=>{let sel=dlnain.manual_sink&&shortName(dlnain.manual_sink)===t.n;h+='<button data-act="dlnain-target" data-sink="'+t.s+'" style="'+(sel?'border-color:#58a6ff;color:#58a6ff':'')+'">'+t.n+'</button>'});h+='</div>'}
h+='<div class="row" style="margin-top:.45rem">';
if(dlnain.running){h+='<button data-act="dlnain-stop" class="danger">⏹ Stop</button>'}else{h+='<button data-act="dlnain-start">▶ Start</button>'}
h+='</div></div>';
let multiOn=!!multi.active;setCookie('multi-output',multiOn?'true':'false');
h+='<div class="media-card route-card '+(multiOn?'on':'off')+'"><h4>🔀 Multi-Output</h4>';
h+='<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">'+badge(multiOn,multiOn?'ACTIVE':'OFF')+' Route one source to all connected Bluetooth outputs.</div>';
h+='<div class="media-meta">Outputs: '+esc((multi.slaves||multi.available_sinks||[]).map(shortName).join(' + ')||'two Bluetooth outputs required');
if(multi.input_pending)h+=' · Waiting for phone/PC playback';else if((multi.routed_inputs||[]).length)h+=' · BT input routed';
h+='</div><div class="row" style="margin-top:.45rem"><button data-act="multi-toggle" class="'+(multiOn?'danger':'')+'">'+(multiOn?'Turn OFF Multi-Output':'Turn ON Multi-Output')+'</button>';
if(multiOn&&(multi.unrouted_inputs||[]).length)h+=' <button data-act="multi-sync">🔄 Route BT Input</button>';
h+='</div>';
h+='</div>';

// Update SVG connections when multi-output changes
function updateAudioPaths(){ routesRefresh(); redraw(); }
el.innerHTML=h;el.onclick=function(e){let b=e.target.closest('[data-act]');if(!b)return;let a=b.dataset.act;if(a==='alexa-start')alexaRouteStart();else if(a==='alexa-stop')alexaRouteStop();else if(a==='alexa-retarget')alexaRouteRetarget();else if(a==='dlnain-start')dlnainStart();else if(a==='dlnain-stop')dlnainStop();else if(a==='dlnain-mode')dlnainMode(b.dataset.mode);else if(a==='dlnain-target')dlnainTarget(b.dataset.sink);else if(a==='multi-toggle')multiOutputToggle();else if(a==='multi-sync')multiOutputSync()}}
async function multiOutputToggle(){let st=await api('/audio/multi-output?action=status');let action=st.active?'stop':'start';msg(action==='start'?'Starting Bluetooth multi-output...':'Stopping Bluetooth multi-output...','info');let r=await api('/audio/multi-output?action='+action);msg(r.ok?(action==='start'?'Multi-output active':'Multi-output disabled'):(r.error||'Multi-output failed'),r.ok?'ok':'err');routesRefresh()}
async function multiOutputSync(){let r=await api('/audio/multi-output?action=sync');msg(r.ok?'Bluetooth input routed':(r.error||'BT input routing failed'),r.ok?'ok':'err');routesRefresh()}
async function alexaRouteStart(){msg('Starting Alexa routing...','info');let r=await api('/audio/route/alexa-bt?action=start');msg(r.ok?'Alexa route started':(r.error||'start failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function alexaRouteStop(){msg('Stopping Alexa routing...','info');let r=await api('/audio/route/alexa-bt?action=stop');msg(r.ok?'Alexa route stopped':(r.error||'stop failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function alexaRouteRetarget(){msg('Retargeting Alexa...','info');let r=await api('/audio/route/alexa-retarget');msg(r.ok?(r.unchanged?'No change needed':'Retargeted to '+shortName(r.new_target)):(r.error||'retarget failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function dlnainStart(){msg('Starting DLNA Input routing...','info');let r=await api('/audio/route/dlna-input/start');msg(r.ok?'DLNA Input started':(r.error||'start failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function dlnainStop(){msg('Stopping DLNA Input routing...','info');let r=await api('/audio/route/dlna-input/stop');msg(r.ok?'DLNA Input stopped':(r.error||'stop failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function dlnainMode(mode){msg('Switching DLNA Input to '+mode+'...','info');let r=await api('/audio/route/dlna-input/mode?mode='+mode);msg(r.ok?'Mode: '+mode:(r.error||'mode failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
async function dlnainTarget(sink){msg('Setting DLNA Input target...','info');let r=await api('/audio/route/dlna-input/target?sink='+encodeURIComponent(sink));msg(r.ok?'Target set':(r.error||'target failed'),r.ok?'ok':'err');setTimeout(routesRefresh,800)}
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
function renderBtDevices(devs){if(!devs||!devs.length)return '<div>No Bluetooth devices listed.</div>';return devs.map(d=>{let mac=d.address||d.mac||'',key=d.key||'',adapter=d.adapter_id||'',profiles=(((d.capabilities||{}).profiles)||[]).map(p=>p.label).join(', ')||'No recognized profiles';return '<div class="media-card" style="min-height:70px;margin:.3rem 0"><h4>'+devIcon(d.kind)+' '+esc(d.name||'Unknown')+' '+badge(!!d.connected,d.connected?'CONNECTED':(d.paired?'PAIRED':'FOUND'))+'</h4><div class="media-meta">MAC: '+esc(mac)+'<br>Adapter: '+esc(adapter||'legacy/unknown')+'<br>Profiles: '+esc(profiles)+'<br>Trusted: '+(d.trusted?'yes':'no')+' · Auto: '+(d.auto_connect?'on':'off')+'</div><div class="row" style="margin-top:.35rem"><button data-i18n="pair" onclick="fallbackBtAction(\'pair\',\''+jsarg(adapter)+'\',\''+jsarg(key)+'\',\''+jsarg(mac)+'\')">Pair</button><button data-i18n="connect" onclick="fallbackBtAction(\'connect\',\''+jsarg(adapter)+'\',\''+jsarg(key)+'\',\''+jsarg(mac)+'\')">Connect</button><button data-i18n="trust" onclick="fallbackBtAction(\'trust\',\''+jsarg(adapter)+'\',\''+jsarg(key)+'\',\''+jsarg(mac)+'\')">Trust</button><button onclick="fallbackBtAction(\''+(d.blocked?'unblock':'block')+'\',\''+jsarg(adapter)+'\',\''+jsarg(key)+'\',\''+jsarg(mac)+'\')">'+(d.blocked?'Unblock':'Block')+'</button><button class="danger" data-i18n="remove" onclick="fallbackBtAction(\'remove\',\''+jsarg(adapter)+'\',\''+jsarg(key)+'\',\''+jsarg(mac)+'\')">Remove</button></div></div>'}).join('')}
async function fallbackBtAction(action,adapter,key,mac){if(action==='pair'){if(!confirm('Start pairing on the selected adapter?'))return;let start=await api('/bt/pairing?action=start&adapter_id='+encodeURIComponent(adapter)+'&device_key='+encodeURIComponent(key)+'&mac='+encodeURIComponent(mac));if(!start.ok){msg(start.error||'Pairing failed','err');return}return fallbackPairPoll(start.pairing.id)}if(action==='remove'&&!confirm('Remove this paired device?'))return;let url=adapter&&key?'/bt/device-action?action='+encodeURIComponent(action)+'&adapter_id='+encodeURIComponent(adapter)+'&device_key='+encodeURIComponent(key):'/bt/'+action+'?mac='+encodeURIComponent(mac),r=await api(url);msg(r.result||r.error,r.ok?'ok':'err');setTimeout(devicesRefresh,700)}
async function fallbackPairPoll(id){let r=await api('/bt/pairing?action=status&operation_id='+encodeURIComponent(id)),challenge=r.challenge||{};if(!r.ok){msg(r.error||'Pairing failed','err');return}if(challenge.state==='waiting_for_user'){let value='',accepted=false;if(challenge.type==='confirmation')accepted=confirm('Bluetooth passkey '+String(challenge.passkey).padStart(6,'0')+' matches?');else if(challenge.type==='pin_code'||challenge.type==='passkey'){value=prompt('Enter Bluetooth PIN/passkey:','')||'';accepted=!!value}else accepted=confirm('Authorize '+challenge.type+'?');await api('/bt/pairing?action=respond&operation_id='+encodeURIComponent(id)+'&accepted='+(accepted?'1':'0')+'&value='+encodeURIComponent(value))}if(r.pairing.state==='pending'){setTimeout(()=>fallbackPairPoll(id),500);return}msg(r.pairing.state==='succeeded'?'Pairing succeeded':(r.pairing.error||'Pairing '+r.pairing.state),r.pairing.state==='succeeded'?'ok':'err');devicesRefresh()}
async function devicesRefresh(){let r=await api('/devices/state');if(r.error){msg(r.error,'err');return}let v2=(r.bluetooth&&r.bluetooth.v2)||{},devs=v2.devices||((r.bluetooth&&r.bluetooth.paired)||[]);$('#dev-bt-list').innerHTML=renderBtDevices(devs);$('#dev-bt-status').textContent=devs.filter(d=>d.paired).length+' paired · '+devs.filter(d=>d.connected).length+' connected'}
async function deviceBtScan(){msg(L('scan')+' Bluetooth...','info');let state=await api('/bt/state'),adapters=(state.adapters||[]).filter(a=>a.present&&a.powered);for(let adapter of adapters)await api('/bt/discovery?action=start&adapter_id='+encodeURIComponent(adapter.id));setTimeout(devicesRefresh,900);msg(L('scan')+' Bluetooth started','ok')}
async function wifiStatus(){let r=await api('/wifi/status');$('#wifi-list').innerHTML='<pre>'+esc(JSON.stringify(r,null,2))+'</pre>'}
async function wifiScan(){msg(L('wifiScanning'),'info');let r=await api('/wifi/scan');if(r.networks){let h=r.networks.map(n=>'<div style="margin:3px 0"><button onclick="$(\'#wifi-ssid\').value=\''+jsarg(n.ssid)+'\'" style="font-size:.72em;padding:2px 8px">'+L('wifiUse')+'</button> '+esc(n.ssid)+' <span style="color:#8b949e">'+esc(n.signal||'')+' '+esc(n.security||'')+'</span></div>').join('');$('#wifi-list').innerHTML=h||L('wifiNone');msg(L('wifiScanDone'),'ok')}else{$('#wifi-list').innerHTML='<pre>'+esc(JSON.stringify(r,null,2))+'</pre>';msg(r.error||L('wifiScanFailed'),'err')}}
async function wifiConnect(){let ssid=$('#wifi-ssid').value.trim(),pw=$('#wifi-pass').value;if(!ssid){msg(L('ssidRequired'),'err');return}let r=await fetch('/wifi/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid,password:pw})}).then(res=>res.json()).catch(e=>({error:e.message}));msg(r.ok?L('wifiConnected'):(r.error||r.out||L('wifiFailed')),r.ok?'ok':'err');wifiStatus()}
async function ytCookieStatus(){let r=await api('/youtube/cookies/status');$('#yt-cookie-status').textContent=JSON.stringify(r,null,2)}
async function ytAgeCheck(){let u=$('#yt-age-url').value.trim();if(!u){msg(L('ytUrlRequired'),'err');return}msg(L('ytChecking'),'info');let r=await api('/youtube/age-check?url='+encodeURIComponent(u));$('#yt-cookie-status').textContent=JSON.stringify(r,null,2);msg(r.ok?L('ytExtractable'):L('ytFailed'),r.ok?'ok':'err')}
async function launchApp(mode){msg(L('launching')+' '+mode+'...','info');let r=await fetch('http://192.168.0.205:8090/mode/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode})}).then(r=>r.json());msg(r.status?'OK: '+mode:(r.error||L('failed')),r.status?'ok':'err')}
async function stopApp(){msg(L('stopping'),'info');let r=await fetch('http://192.168.0.205:8090/mode/stop',{method:'POST'}).then(r=>r.json());msg(r.message||L('stopped'),'ok')}
// Terminal
let term=null,termWs=null,termFit=null;
function termSendResize(){if(term&&termWs&&termWs.readyState===1){termWs.send(JSON.stringify({resize:{cols:term.cols,rows:term.rows}}))}}
function termFitNow(){if(termFit){termFit.fit();termSendResize()}}
function termInit(){if(term)return;term=new Terminal({theme:{background:'#0d1117',foreground:'#c9d1d9',cursor:'#58a6ff'},fontSize:13,fontFamily:'monospace',cursorBlink:true,scrollback:0,convertEol:false,disableStdin:false});termFit=new FitAddon.FitAddon();term.loadAddon(termFit);term.open(document.getElementById('terminal'));setTimeout(termFitNow,150);setTimeout(termFitNow,450);term.onData(d=>{if(termWs&&termWs.readyState===1)termWs.send(JSON.stringify({input:d}))});term.onResize(()=>termSendResize());window.addEventListener('resize',()=>setTimeout(termFitNow,120));msg(L('termReady'),'info')}
function termDrawSnapshot(output,cursor){let text=output||'';let lines=text.split(/\r?\n/);let row=1,col=1;if(cursor&&Number.isFinite(cursor.y)&&Number.isFinite(cursor.x)){row=Math.max(1,Math.min(term.rows,cursor.y+1));col=Math.max(1,Math.min(term.cols,cursor.x+1))}else{let last=lines.length?lines[lines.length-1]:'';row=Math.max(1,Math.min(term.rows,lines.length));col=Math.max(1,Math.min(term.cols,(last||'').length+1))}term.write('\x1b[?25h\x1b[H\x1b[2J'+text+'\x1b['+row+';'+col+'H')}
function termConnect(){termInit();let host=location.hostname||'localhost';if(termWs&&termWs.readyState===1)return;termWs=new WebSocket('ws://'+host+':8098');termWs.onopen=()=>{msg(L('connected'),'ok');$('#term-status').textContent=L('connected');term.clear();termWs.send(JSON.stringify({action:'attach',session:'RPi',cols:term.cols,rows:term.rows}))};termWs.onmessage=e=>{try{let d=JSON.parse(e.data);if(d.full&&d.output!==undefined){termDrawSnapshot(d.output,d.cursor)}else if(d.output){term.write(d.output)}}catch{}};termWs.onclose=()=>{$('#term-status').textContent=L('disconnected');msg(L('disconnected'),'info')};termWs.onerror=()=>msg(L('connectionError'),'err')}
function termDisconnect(){if(termWs){termWs.close();termWs=null}$('#term-status').textContent=L('disconnected')}
// Feedback Modal
function openFeedback(){$('#feedback-desc').value='';$('#feedback-modal').classList.add('show')}
function closeFeedback(){$('#feedback-modal').classList.remove('show')}
async function submitFeedback(){let t=$('#feedback-type').value,d=$('#feedback-desc').value.trim();if(!d){msg(L('feedbackRequired'),'err');return}closeFeedback();msg(L('feedbackSending'),'info');let r=await fetch('/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:t,description:d})}).then(res=>res.json()).catch(e=>({error:e.message}));if(r.ok){msg(L('feedbackSuccess')+' '+r.file,'ok')}else{msg(r.error||L('feedbackFailed'),'err')}}
setInterval(()=>{st();updBr()},3000);playerEnter();addTips();applyLang();
let sp=new URLSearchParams(window.location.search);let shared=sp.get('share_url')||sp.get('text');
if(shared&&shared.match(/http[s]?:\/\/[^\s]+/)){$('#url').value=shared.match(/http[s]?:\/\/[^\s]+/)[0];play();}
"""

QO="\n".join(f'<option value="{k}"{" selected" if k==DQ else ""}>{k}</option>' for k in QUALITY)

def _load_static_page():
    """Try to load new static HTML page. Returns None if not available."""
    try:
        static_html = os.path.join(os.path.dirname(__file__), "rpi_dashboard", "static", "index.html")
        if os.path.isfile(static_html):
            with open(static_html, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace template placeholders
            content = content.replace("{{QUALITY_OPTIONS}}", QO)
            return content
    except Exception as e:
        print(f"[WARN] Could not load static page: {e}", file=sys.stderr)
    return None


def page():
    """Return WebUI HTML. Try new static files first, fallback to inline."""
    # Try new static files
    static_page = _load_static_page()
    if static_page:
        return static_page
    # Fallback to old inline HTML
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="manifest" href="/manifest.json">
<title>RPi-TV</title><style>{CSS}</style></head><body>
<div id="topbar"><h1 id="app-title">RPi-TV</h1><div style="display:flex;gap:.5rem;align-items:center"><button class="feedback-btn" onclick="openFeedback()" data-i18n="feedbackBtn" style="font-size:.78rem;padding:.22rem .42rem;border-radius:999px;border:1px solid #30363d;background:#161b22;color:#c9d1d9;cursor:pointer">💬 Feedback</button><div id="lang-switch"><button class="lang-btn" data-lang-btn="en" onclick="setLang('en')" title="English" aria-label="English">🇬🇧</button><button class="lang-btn" data-lang-btn="cz" onclick="setLang('cz')" title="Čeština" aria-label="Čeština">🇨🇿</button></div></div></div><div id="security-banner"></div><div id="toast"></div>
<div class="tabs">
<button id="tab-player" class="tab active" data-t="player" data-i18n="player" data-icon="🎬" onclick="sw('player')">🎬 Player</button>
<button id="tab-apps" class="tab" data-t="apps" data-i18n="apps" data-icon="🚀" onclick="sw('apps')">🚀 Apps</button>
<button id="tab-cec" class="tab" data-t="cec" data-i18n="cec" data-icon="📺" onclick="sw('cec')">📺 CEC</button>
<button id="tab-audio" class="tab" data-t="audio" data-i18n="audio" data-icon="🔊" onclick="sw('audio');taRefresh()">🔊 Audio</button>
<button id="tab-devices" class="tab" data-t="devices" data-i18n="devices" data-icon="🧩" onclick="sw('devices');devicesRefresh();wifiStatus()">🧩 Devices</button>
<button id="tab-terminal" class="tab" data-t="terminal" data-i18n="terminal" data-icon="💻" onclick="sw('terminal')">💻 Terminal</button>
</div>
<div id="p-player" class="pnl active"><div class="sec"><h3 data-tip="sectionPlayer" style="display:none">Player help</h3>
<div class="row"><div class="url-wrap"><input id="url" data-i18n="inputUrl" data-i18n-attr="placeholder" placeholder="YouTube or direct URL..." oninput="schedulePreview()"><button class="url-paste" data-i18n="pasteClipboard" data-i18n-attr="title" onclick="pasteClipboardUrl()" title="Paste clipboard" aria-label="Paste clipboard">📋</button></div><select id="qual" style="width:auto;min-width:88px">{QO}</select></div>
<div id="player-preview"></div>
<div class="row" style="margin-top:.3rem">
<button data-i18n="play" data-icon="▶" onclick="play()">▶ Play</button><button onclick="pause()" data-i18n="pause" data-i18n-attr="aria-label" aria-label="Pause">⏸</button><button onclick="stop()" class="danger" data-i18n="stop" data-i18n-attr="aria-label" aria-label="Stop">⏹</button>
<button onclick="seek(-10)" data-i18n="rewind10" data-i18n-attr="aria-label" aria-label="Rewind 10 seconds">⏪10</button><button onclick="seek(10)" data-i18n="forward10" data-i18n-attr="aria-label" aria-label="Forward 10 seconds">10⏩</button>
<button onclick="vol(-10)" data-i18n="volumedown" data-i18n-attr="aria-label" aria-label="Volume down">🔉</button><button onclick="vol(10)" data-i18n="volumeup" data-i18n-attr="aria-label" aria-label="Volume up">🔊</button><button onclick="mute()" style="font-size:.85rem" data-i18n="mute" data-i18n-attr="aria-label" aria-label="Mute">🔇</button></div>
<div style="margin-top:.4rem"><div style="display:flex;align-items:center;gap:.4rem"><span id="stime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span><input type="range" id="sbar" min="0" max="100" value="0" step="0.1" style="flex:1;height:6px;accent-color:#58a6ff;cursor:pointer" oninput="seekTo(this.value)" ontouchstart="seeking=true" ontouchend="seeking=false"><span id="dtime" style="font-size:.75rem;color:#8b949e;min-width:36px">0:00</span></div></div></div>
<div class="sec"><h3 data-i18n="status">Status</h3><div id="st">—</div></div>
<div class="sec"><h3 data-i18n="quick" data-tip="sectionQuick">Quick</h3><div class="row">
<button onclick="qu('https://www.youtube.com/watch?v=dQw4w9WgXcQ')" style="font-size:.75rem">🎵 Rick Astley</button>
<button onclick="qu('https://www.youtube.com/watch?v=9bZkp7q19f0')" style="font-size:.75rem">🎵 Gangnam</button></div></div>
<div class="sec"><h3 data-i18n="ytAge" data-tip="sectionAgeCookies">YouTube Age / Cookies</h3><div class="media-meta" data-i18n="ytAgeDesc">Checks cookie freshness without exposing cookie values. Use this when age-restricted videos fail.</div><div class="row" style="margin-top:.35rem"><input id="yt-age-url" data-i18n="inputUrl" data-i18n-attr="placeholder" placeholder="YouTube URL for age-check..." style="flex:1"><button data-icon="🍪" data-i18n="cookieStatus" onclick="ytCookieStatus()">🍪 Cookie status</button><button data-icon="🔞" data-i18n="ageCheck" onclick="ytAgeCheck()">🔞 Age check</button></div><pre id="yt-cookie-status" data-i18n="clickCookieStatus">Click Cookie status</pre></div></div>
</div>
<div id="p-apps" class="pnl"><div class="sec"><h3 data-i18n="appsLaunch" data-tip="sectionApps">Spustit aplikaci</h3>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:.5rem">
<button onclick="launchApp('steamlink')" style="padding:12px;font-size:1rem">🎮 Steam Link</button>
<button onclick="launchApp('gfn')" style="padding:12px;font-size:1rem">🎯 GeForce Now</button>
<button onclick="launchApp('mpv')" style="padding:12px;font-size:1rem" data-i18n="appsMpv">🎬 MPV Přehrávač</button>
<button onclick="launchApp('spotify')" style="padding:12px;font-size:1rem">🎵 Spotify</button>
<button onclick="launchApp('amazon')" style="padding:12px;font-size:1rem">🎶 Amazon Music</button>
<button onclick="stopApp()" style="padding:12px;font-size:1rem;color:#f85149;border:2px solid #f85149" data-i18n="appsStopReturn">⏹ ZASTAVIT & VRÁTIT SE</button>
</div></div>
<div class="sec"><h3 data-i18n="appsReturn" data-tip="sectionAppsReturn">Návrat do Dashboardu</h3>
<div style="font-size:.85em;color:#c9d1d9" data-i18n="appsReturnDesc">
• <b>Ctrl+C</b> — ukončí většinu aplikací<br>
• <b>Ctrl+Q</b> — ukončí Steam Link<br>
• <b>tlačítko ZASTAVIT</b> — vynutí návrat<br>
• Aplikace běží přímo na TV, dashboard se automaticky vrátí po ukončení
</div></div></div>
<div id="p-cec" class="pnl"><div class="sec"><h3 data-i18n="cecPower" data-tip="sectionCecPower">Power</h3><div class="row">
<button onclick="cec('on 0')" data-i18n="cecOn" data-icon="🟢">🟢 On</button><button onclick="cec('standby 0')" class="danger" data-i18n="cecOff" data-icon="🔴">🔴 Off</button>
<button onclick="cecScan()" data-i18n="cecScan" data-icon="🔍">🔍 Scan</button></div></div>
<div class="sec"><h3 data-i18n="cecBridge" data-tip="sectionCecBridge">Remote→MPV Bridge</h3><div class="row">
<button id="brb" onclick="cecBr()" data-i18n="cecStart" data-icon="▶">▶ Start</button><span id="brs" style="font-size:.75em;color:#8b949e" data-i18n="disconnected">Disconnected</span></div>
<div style="font-size:.7em;color:#666" data-i18n="cecBridgeDesc">Play/Pause, Stop, Seek, Vol via TV remote</div></div>
<div class="sec"><h3 data-i18n="cecNav" data-tip="sectionCecNav">Nav</h3><div class="cec-grid">
<button onclick="cecKey('menu')" aria-label="TV Menu">📋</button><button onclick="cecKey('up')" aria-label="TV Up">▲</button><button onclick="cecKey('channels+')">CH+</button>
<button onclick="cecKey('left')" aria-label="TV Left">◀</button><button onclick="cecKey('select')" style="font-size:.7rem">OK</button><button onclick="cecKey('right')" aria-label="TV Right">▶</button>
<button onclick="cecKey('back')" aria-label="TV Back">◀◀</button><button onclick="cecKey('down')" aria-label="TV Down">▼</button><button onclick="cecKey('channels-')">CH-</button></div></div>
<div class="sec"><h3 data-i18n="cecVol" data-tip="sectionCecVol">Vol</h3><div class="vol-row">
<button onclick="cec('voldown')" aria-label="TV Volume down">🔉−</button><button onclick="cec('mute')" aria-label="TV Mute">🔇</button><button onclick="cec('volup')" aria-label="TV Volume up">🔊+</button></div></div>
<div class="sec"><h3 data-i18n="cecInput" data-tip="sectionCecInput">Input</h3><div class="row">
<button onclick="cecIn(1)">HDMI1</button><button onclick="cecIn(2)">HDMI2</button><button onclick="cecIn(3)">HDMI3</button></div></div>
<div class="sec"><h3 data-i18n="cecDevices" data-tip="sectionCecDevices">Devices</h3><div id="cdev" data-i18n="clickScan" style="font-size:.8em;color:#8b949e">Click Scan</div></div></div>
<div id="p-audio" class="pnl">
<div class="sec"><div class="media-head"><div><h3 data-i18n="audioTitle" data-tip="sectionAudio">Audio & Media</h3><div class="media-meta" data-i18n="audioDesc">Primary audio routing and mixer. Speaker pairing lives in Devices; output routing lives here.</div></div><div class="row"><button onclick="taSwitch('bt')">🎧 BT</button><button onclick="taSwitch('hdmi')">📺 HDMI</button><button onclick="taSwitch('dlna')">📡 DLNA</button><button data-i18n="refresh" data-icon="🔄" onclick="taRefresh()">🔄 Refresh</button></div></div><div class="media-meta"><span data-i18n="taDefault">Default sink:</span> <span id="ta-default">—</span></div></div>
<div class="media-grid"><div><div class="sec"><h3 data-i18n="outputSinks" data-tip="sectionOutputSinks">Output Sinks</h3><div id="ta-sinks" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div><div><div class="sec"><h3 data-i18n="inputSources" data-tip="sectionInputSources">Input Sources</h3><div id="ta-sources" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div></div></div>
<div class="sec"><h3 data-i18n="mixer" data-tip="sectionMixer">Mixer — Active Streams</h3><div id="ta-mixer" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3 data-i18n="audioRouting" data-tip="sectionAudioRouting">Audio Routing & Patchbay</h3><div id="ta-matrix" style="margin-bottom:1rem;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:0.5rem"></div><div id="ta-routes" class="media-grid" style="grid-template-columns:1fr">Loading...</div></div>
<div class="sec"><h3 data-i18n="dlnaLatency" data-tip="sectionDlnaLatency">DLNA Latency Compensation</h3><div style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">
<label style="font-size:.72rem;color:#8b949e" data-i18n="audioDelay">Audio delay (ms):</label>
<input type="number" id="ta-lat-dlna-offset" value="0" min="-5000" max="5000" step="50" style="width:80px">
<button data-icon="💾" data-i18n="saveApply" onclick="taSetLatency('dlna_output_offset_ms',$('#ta-lat-dlna-offset').value)">💾 Save + Apply</button>
<span class="media-meta">Applies mpv audio-delay in milliseconds for DLNA sync. Positive delays audio; negative advances audio/video sync.</span></div></div>
<div class="sec"><h3 data-i18n="diagnostics" data-tip="sectionDiagnostics">Diagnostics</h3><div id="ta-summary" class="media-meta" data-i18n="clickRefresh">Click Refresh</div><details style="margin-top:.5rem"><summary class="media-meta" style="cursor:pointer" data-i18n="taRaw">Raw technical JSON</summary><pre id="ta-raw" data-i18n="clickRefresh">Click Refresh</pre></details></div>
</div>
<div id="p-devices" class="pnl">
<div class="sec"><div class="media-head"><div><h3 data-i18n="devicesTitle" data-tip="sectionDevices">Devices</h3><div class="media-meta" data-i18n="devicesDesc">Pair and connect hardware here. Speaker output routing and volume remain in Audio.</div></div><div class="row"><button data-i18n="refresh" data-icon="🔄" onclick="devicesRefresh()">🔄 Refresh</button></div></div></div>
<div class="media-grid"><div class="sec"><h3 data-i18n="btPair" data-tip="sectionBluetooth">Bluetooth Pairing</h3><div class="row"><button onclick="deviceBtScan()">🔍 Scan</button><span id="dev-bt-status" class="media-meta">—</span></div><div id="dev-bt-list" data-i18n="clickScanRefresh" class="media-meta" style="margin-top:.4rem">Click Scan or Refresh</div></div>
<div class="sec"><h3 data-i18n="wifiConfig" data-tip="sectionWifi">Wi-Fi Configuration</h3><div class="row"><button onclick="wifiStatus()">📶 Status</button><button onclick="wifiScan()">🔍 Scan Wi-Fi</button></div><div class="row" style="margin-top:.35rem"><input id="wifi-ssid" data-i18n="ssid" data-i18n-attr="placeholder" placeholder="SSID" style="flex:1"><input id="wifi-pass" data-i18n="password" data-i18n-attr="placeholder" type="password" placeholder="Password (kept in browser only)" style="flex:1"><button data-i18n="connect" onclick="wifiConnect()">Connect</button></div><div id="wifi-list" class="media-meta" style="margin-top:.4rem">—</div></div></div>
<div class="sec"><h3 data-i18n="roles" data-tip="sectionRoles">Suggested Device Roles</h3><div class="media-meta" data-i18n="rolesDesc">• Speakers/headphones/soundbars: pair/connect/trust here, then choose routing in Audio.<br>• Xbox controllers/gamepads: pair/connect/trust here for input use; no audio routing is applied.<br>• Remote microphone and USB Alexa input are shown in Audio as sources.<br>• Future additions: HDMI-CEC device inventory, Tailscale status, storage/USB device health.</div></div>
</div>
<div id="p-terminal" class="pnl">
<div class="sec"><h3 data-i18n="hwStatsTitle">HW Stats & CPU Masks</h3>
<div class="row" style="margin-bottom:.35rem"><button onclick="loadHwStats();loadSysStatus()" style="font-size:.75rem" data-i18n="hwUpdateBtn" data-icon="🔄">🔄 Update</button><button id="hw-live-btn" onclick="toggleHwLive()" style="font-size:.75rem" data-i18n="hwLiveBtn" data-icon="▶">▶ Live monitoring</button></div>
<div id="hw-stats" style="font-size:.75rem;color:#8b949e;font-family:monospace;white-space:pre-wrap" data-i18n="hwLoading">Loading HW stats...</div>
<div id="sys-status" style="margin-top:.5rem;font-size:.75rem;color:#8b949e;font-family:monospace;white-space:pre-wrap" data-i18n="sysLoading">Loading CPU masks...</div></div>
<div class="sec"><h3 data-tip="sectionTerminal" style="display:none">Terminal help</h3>
<div class="row" style="margin-bottom:.4rem"><button data-i18n="termConnect" data-icon="🔌" onclick="termConnect()">🔌 Connect</button><button data-i18n="termDisconnect" data-icon="⏹" onclick="termDisconnect()" class="danger">⏹ Disconnect</button><span id="term-status" data-i18n="disconnected" style="font-size:.75em;color:#8b949e">Disconnected</span></div>
<div id="terminal"></div></div>
<div class="sec"><h3 data-i18n="restartTitle">Restart Actions</h3><div class="row"><button onclick="restartMpv()" class="danger" style="font-size:.75rem" data-i18n="restartMpv" data-icon="🔄">🔄 Restart mpv</button><button onclick="restartDashboard()" style="font-size:.75rem" data-i18n="restartDashboard" data-icon="🔄">🔄 Restart Dashboard</button><button onclick="restartRpi()" class="danger" style="font-size:.75rem" data-i18n="restartRpi" data-icon="🔄">🔄 Restart RPi</button></div></div></div>
<div id="feedback-modal" class="modal">
  <div class="modal-content">
    <button class="modal-close" onclick="closeFeedback()">×</button>
    <h3 data-i18n="feedbackTitle">💬 Submit Feedback</h3>
    <div>
      <label data-i18n="feedbackTypeLabel" style="display:block;margin-bottom:.2rem;font-size:.85rem;color:#8b949e">Type:</label>
      <select id="feedback-type" style="width:100%;background:#0d1117;border:1px solid #30363d;color:#c9d1d9;padding:.4rem;border-radius:.3rem">
        <option value="bug" data-i18n="feedbackBug">Bug Report</option>
        <option value="feature" data-i18n="feedbackFeature">Feature Request</option>
      </select>
    </div>
    <div style="margin-top:.4rem">
      <label data-i18n="feedbackDescLabel" style="display:block;margin-bottom:.2rem;font-size:.85rem;color:#8b949e">Description:</label>
      <textarea id="feedback-desc" data-i18n-attr="placeholder" placeholder="Please describe the issue or your feature request..." style="width:100%;height:100px;background:#0d1117;border:1px solid #30363d;color:#c9d1d9;padding:.4rem;border-radius:.3rem;resize:vertical;box-sizing:border-box"></textarea>
    </div>
    <button onclick="submitFeedback()" style="width:100%;margin-top:.4rem" data-i18n="feedbackSubmit">Submit</button>
  </div>
</div>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
<script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
<script>{JS}</script></body></html>"""


# Rate limiting
_rate_limit_cache: dict[str, float] = {}
from config import RATE_LIMIT_SECONDS

def _is_allowed_ip(client_ip: str) -> bool:
    """Return True if *client_ip* belongs to one of ALLOWED_SUBNETS.
    Uses ipaddress module for robust CIDR checking.
    """
    return api_middleware.is_allowed_ip(client_ip, ALLOWED_SUBNETS)


def _check_rate_limit(client_ip: str) -> bool:
    """Check if request is rate limited. Returns True if allowed."""
    return api_middleware.check_rate_limit(
        client_ip,
        _rate_limit_cache,
        window_seconds=RATE_LIMIT_SECONDS,
    )


_hw_stats_freq_cache = {"data": [None, None, None, None], "time": 0}

class H(BaseHTTPRequestHandler):
    """HTTP request handler for RPi-TV Dashboard WebUI."""
    server_version="RPi-TV/4.2"
    def _send_cors_headers(self):
        origin = self.headers.get("Origin")
        cors_origin = api_middleware.allowed_cors_origin(origin, ALLOWED_SUBNETS)
        self.send_header("Access-Control-Allow-Origin", cors_origin)
        if cors_origin == origin:
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def sj(self,c,o):
        d=json.dumps(o,ensure_ascii=False).encode()
        self.send_response(c);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(d)))
        self._send_cors_headers()
        self.end_headers();self.wfile.write(d)

    def st(self,c,b,ct="text/html;charset=utf-8"):
        d=b.encode()
        self.send_response(c);self.send_header("Content-Type",ct)
        self.send_header("Content-Length",str(len(d)))
        self._send_cors_headers()
        self.end_headers();self.wfile.write(d)
    def do_GET(self):
        p=urlparse(self.path);q=parse_qs(p.query);path=p.path

        # IP allowlist check
        if not _is_allowed_ip(self.client_address[0]):
            self.sj(403, {"error": "Forbidden – IP not allowed"})
            return
        # Rate limit GET endpoints that trigger system actions
        action_endpoints = {
            "/system/reboot", "/devices/bt/scan", "/wifi/scan", "/audio/default-sink",
            "/audio/latency", "/dlna/select", "/dlna/connect", "/dlna/disconnect",
            "/keepalive", "/dlna/scan", "/youtube/age-check", "/media/preview",
            "/mpv/play", "/mpv/stop", "/mpv/toggle", "/mpv/seek", "/mpv/volume", "/mpv/mute"
        }
        if path in action_endpoints:
            if not _check_rate_limit(self.client_address[0]):
                self.send_error(429, "Rate limited")
                return

        # Placeholder modes endpoint
        if path == "/modes":
            self.sj(200, {"ok": True, "modes": ["player","audio","devices","terminal"], "note": "Placeholder endpoint"})
            return

        # Static file serving
        if path.startswith("/static/"):
            static_dir = os.path.join(os.path.dirname(__file__), "rpi_dashboard", "static")
            file_path = os.path.join(static_dir, path[8:])  # Remove /static/
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1]
                mime_types = {".css": "text/css", ".js": "application/javascript", ".html": "text/html", ".json": "application/json"}
                mime = mime_types.get(ext, "application/octet-stream")
                with open(file_path, "r") as f:
                    content = f.read()
                self.st(200, content, mime)
                return
            else:
                self.send_error(404, "File not found")
                return

        try:
            registry_first = {
                "/bt/state",
                "/bt/discovery",
                "/bt/adapter-power",
                "/bt/discoverable",
                "/bt/settings",
                "/bt/device-action",
                "/audio/multi-output",
                "/audio/bluetooth-profiles",
                "/audio/mute-state",
                "/bt/device-profile",
                "/bt/device-hid",
                "/bt/transfers",
                "/bt/files",
                "/bt/diagnostics",
                "/bt/file-send",
                "/bt/file-cancel",
                "/bt/operation",
                "/bt/media",
                "/bt/pairing",
            }
            if path in registry_first:
                handler = get_route(path)
                if handler:
                    return self.sj(200, handler(q))
            if path in ("/","/index.html"): return self.st(200,page())
            elif path=="/favicon.ico": return self.st(204,"","image/x-icon")
            elif path=="/manifest.json":
                import json
                m = {
                    "name": "RPi Dashboard",
                    "short_name": "RPiDash",
                    "start_url": "/",
                    "display": "standalone",
                    "background_color": "#0d1117",
                    "theme_color": "#0d1117",
                    "icons": [{"src": 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="%23238636"/><text x="50" y="50" font-size="50" text-anchor="middle" dy=".3em" fill="white">📺</text></svg>', "sizes": "192x192 512x512", "type": "image/svg+xml"}],
                    "share_target": {"action": "/", "method": "GET", "params": {"title": "title", "text": "text", "url": "share_url"}}
                }
                return self.st(200,json.dumps(m),"application/manifest+json")
            elif path=="/mpv/play":
                u=(q.get("url")or[""])[0].strip();ql=(q.get("q")or[None])[0]
                resume=(q.get("resume")or["0"])[0] not in ("0", "", "false", "False")
                if not u: return self.sj(400,{"error":"no url"})
                self.sj(200,mpv_start(u,ql,resume))
            elif path=="/mpv/stop":
                memory = save_mpv_resume_memory() if mpv_ipc_socket_live() else None
                stopped=mpv_stop();self.sj(200,{"ok":True,"memory":memory,"stop":stopped})
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
            elif path=="/mpv/memory":
                u=(q.get("url")or[""])[0].strip()
                if not u: return self.sj(400,{"error":"no url"})
                memory = get_mpv_memory_for_url(u)
                self.sj(200,{"ok":True,"memory":memory})
            elif path=="/mpv/memory/clear":
                u=(q.get("url")or[""])[0].strip()
                if not u: return self.sj(400,{"error":"no url"})
                cleared = clear_mpv_memory_for_url(u)
                self.sj(200,{"ok":True,"cleared":cleared})
            elif path=="/mpv/memory-save":
                if mpv_ipc_socket_live():
                    memory = save_mpv_resume_memory()
                    self.sj(200,{"ok":True,"memory":memory})
                else:
                    self.sj(200,{"ok":True,"memory":"mpv not running"})
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
                self.sj(200,cec_cmd("active-source phys-addr=1.0.0.0"))
            elif path=="/cec/scan": self.sj(200,{"ok":True,"out":cec_scan()})
            elif path=="/cec/br/start": self.sj(200,br_start())
            elif path=="/cec/br/stop": br_stop();self.sj(200,{"ok":True})
            elif path=="/cec/br/st": self.sj(200,br_st())
            elif path=="/play":
                self.sj(410,{"ok":False,"deprecated":True,"error":"Kodi launcher was removed; use /mpv/play or the Player tab."})
            elif path=="/kodi/st": self.sj(410,{"ok":False,"deprecated":True,"error":"Kodi support was removed from this RPi."})
            elif path=="/kodi/status": self.sj(410,{"ok":False,"deprecated":True,"error":"Kodi support was removed from this RPi."})
            elif path=="/selftest/testaudio": self.sj(200,selftest_testaudio())
            elif path=="/audio/state": self.sj(200,audio_state())
            elif path=="/audio/matrix": self.sj(200,get_audio_matrix())
            elif path=="/audio/matrix/link":
                o=(q.get("out")or[""])[0]; i=(q.get("in")or[""])[0]; s=(q.get("state")or["1"])[0]
                self.sj(200,audio_matrix_link(o,i,s))
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
                if a=="status":
                    running,target,mid=_alexa_loopback_running()
                    return self.sj(200,{"ok":True,"route":"alexa_to_bt","on":running,"target":target,"module_id":mid,"default_sink":_get_default_sink()})
                self.sj(200,audio_route_alexa_bt(a))
            elif path=="/audio/route/alexa-retarget":
                self.sj(200,_retarget_alexa())
            elif path=="/audio/route/dlna-input/status":
                running,src=_dlnain_loopback_running()
                cfg=_load_dlnain_mode()
                target=_resolve_dlnain_target() if running else None
                self.sj(200,{"ok":True,"running":running,"source":src,"mode":cfg.get("mode","follow"),"manual_sink":cfg.get("manual_sink"),"active_target":target,"default_sink":_get_default_sink()})
            elif path=="/audio/route/dlna-input/start":
                self.sj(200,_dlnain_start())
            elif path=="/audio/route/dlna-input/stop":
                self.sj(200,_dlnain_stop())
            elif path=="/audio/route/dlna-input/mode":
                mode=(q.get("mode")or["follow"])[0].strip()
                if mode not in ("follow","manual"): return self.sj(400,{"error":"mode must be follow or manual"})
                cfg=_load_dlnain_mode(); cfg["mode"]=mode; _save_dlnain_mode(cfg)
                self.sj(200,{"ok":True,"mode":mode})
            elif path=="/audio/route/dlna-input/target":
                sink=(q.get("sink")or[""])[0].strip()
                if not sink: return self.sj(400,{"error":"no sink"})
                cfg=_load_dlnain_mode(); cfg["manual_sink"]=sink; _save_dlnain_mode(cfg)
                # If running in manual mode, retarget now
                if cfg.get("mode")=="manual":
                    _dlnain_retarget(sink)
                self.sj(200,{"ok":True,"manual_sink":sink})
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

            elif path=="/youtube/cookies/status": self.sj(200,youtube_cookie_status())
            elif path=="/youtube/age-check":
                u=(q.get("url")or[""])[0].strip()
                self.sj(200,youtube_age_check(u))
            elif path=="/media/preview":
                u=(q.get("url")or[""])[0].strip()
                self.sj(200,media_preview(u))
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
                seconds=(q.get("seconds")or["5"])[0]
                self.sj(200,devices_service.bluetooth_scan_devices(seconds))
            elif path=="/bt/controller":
                self.sj(200,{"ok":True,"controller":devices_service.bluetooth_controller_status()})
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
            elif path=="/dlna/renderer/status":
                self.sj(200,dlna_renderer_status())
            elif path=="/dlna/renderer/start":
                self.sj(200,dlna_renderer_start())
            elif path=="/dlna/renderer/stop":
                self.sj(200,dlna_renderer_stop())
            elif path=="/bt/trust":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                self.sj(200,get_route(path)(q))
            elif path=="/bt/pair":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                self.sj(200,get_route(path)(q))
            elif path=="/bt/connect":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                result=get_route(path)(q)
                bt_sink=None
                if result.get("ok"):
                    for _ in range(10):
                        bt_sink=next((s["name"] for s in _pactl_lines("sinks") if s["name"].startswith("bluez_")),None)
                        if bt_sink: break
                        time.sleep(1)
                    if bt_sink: _keepalive_start(bt_sink)
                result.update({"bt_sink":bt_sink,"keepalive":_keepalive_status()})
                self.sj(200,result)
            elif path=="/bt/disconnect":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                result=get_route(path)(q)
                if result.get("ok"): _keepalive_stop()
                result.update({"keepalive":_keepalive_status()})
                self.sj(200,result)
            elif path=="/bt/remove":
                mac=(q.get("mac")or[""])[0].strip()
                if not mac: return self.sj(400,{"error":"no mac"})
                self.sj(200,get_route(path)(q))
            elif path=="/system/hw-stats":
                def _cpu_sample():
                    out=[]
                    with open("/proc/stat") as f:
                        for line in f:
                            if re.match(r"^cpu[0-3] ", line):
                                p=[int(x) for x in line.split()[1:]]
                                idle=p[3]+p[4]
                                total=sum(p)
                                out.append((total,idle))
                    return out
                a=_cpu_sample(); __import__('time').sleep(0.35); b=_cpu_sample()
                cpu=[]
                for (t0,i0),(t1,i1) in zip(a,b):
                    dt=t1-t0; di=i1-i0
                    cpu.append(round(100*(dt-di)/dt,1) if dt>0 else 0.0)
                mem={}
                with open("/proc/meminfo") as f:
                    for line in f:
                        k,v=line.split(":",1); mem[k]=int(v.split()[0])
                total_mb=mem.get("MemTotal",0)//1024
                avail_mb=mem.get("MemAvailable",0)//1024
                used_mb=max(0,total_mb-avail_mb)
                st=os.statvfs("/")
                total_gb=round(st.f_blocks*st.f_frsize/1024/1024/1024,1)
                free_gb=round(st.f_bfree*st.f_frsize/1024/1024/1024,1)
                avail_gb=round(st.f_bavail*st.f_frsize/1024/1024/1024,1)
                used_gb=round(total_gb-free_gb,1)
                temp_c=None
                for tp in ("/sys/class/thermal/thermal_zone0/temp","/sys/class/thermal/thermal_zone1/temp"):
                    try:
                        with open(tp) as f:
                            temp_c=round(int(f.read().strip())/1000,1); break
                    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
                global _hw_stats_freq_cache
                now = time.monotonic()
                if now - _hw_stats_freq_cache["time"] > 2.0:
                    freq = []
                    for i in range(4):
                        try:
                            with open(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq") as f:
                                freq.append(int(f.read().strip()) // 1000)
                        except Exception:
                            freq.append(None)
                    _hw_stats_freq_cache["data"] = freq
                    _hw_stats_freq_cache["time"] = now
                else:
                    freq = _hw_stats_freq_cache["data"]
                gpu={"core_mhz": None, "temp_c": temp_c}
                try:
                    raw=subprocess.check_output(["vcgencmd","measure_clock","core"], text=True, timeout=2).strip()
                    gpu["core_mhz"]=int(raw.split("=")[-1])//1000000
                except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
                try:
                    raw=subprocess.check_output(["vcgencmd","measure_temp"], text=True, timeout=2).strip()
                    gpu["temp_c"]=round(float(raw.split("=")[-1].replace("'C","")),1)
                except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
                with open("/proc/uptime") as f:
                    up=int(float(f.read().split()[0])); h=up//3600; m=(up%3600)//60; s=up%60
                self.sj(200,{"cpu":cpu,"loadavg":list(os.getloadavg()),"temp_c":temp_c,"freq_mhz":freq,"gpu":gpu,"ram":{"used_mb":used_mb,"total_mb":total_mb,"percent":round(100*used_mb/total_mb,1) if total_mb else 0},"disk":{"used_gb":used_gb,"total_gb":total_gb,"free_gb":free_gb,"avail_gb":avail_gb,"percent":round(100*used_gb/total_gb,1) if total_gb else 0},"uptime":f"{h}h {m}m {s}s"})
            elif path=="/system/https-info":
                host=(self.headers.get('Host','').split(':')[0] or '192.168.0.205')
                names, ips = _dashboard_hostnames_and_ips()
                self.sj(200,{"ok":True,"http_port":PORT,"https_port":HTTPS_PORT,"friendly_http_port":HTTP_PORT,"friendly_https_port":HTTPS_PORT_ALT,"cert_exists":os.path.exists(HTTPS_CERT_FILE),"https_url":f"https://{host}:{HTTPS_PORT}/","friendly_https_url":f"https://{host}/","friendly_http_url":f"http://{host}/","names":names,"ips":ips})
            elif path=="/system/status":
                # Get CPU mask info for all services
                try:
                    mpv_pid = subprocess.check_output(["pgrep", "-x", "mpv"], text=True).strip().splitlines()[0]
                except Exception:
                    mpv_pid = ""
                mpv_mask = "N/A"
                mpv_cores = "N/A"
                if mpv_pid:
                    mpv_mask = subprocess.check_output(["taskset", "-p", mpv_pid], text=True).strip().split(":")[-1].strip()
                    # Parse mask to core list
                    try:
                        mask_val = int(mpv_mask, 16)
                        cores = [str(i) for i in range(4) if mask_val & (1 << i)]
                        mpv_cores = ",".join(cores) if cores else "none"
                    except Exception:
                        mpv_cores = "?"

                dash_pid = subprocess.check_output(["systemctl", "show", "dashboard@milhy777", "-p", "MainPID", "--value"], text=True).strip()
                dash_mask = "N/A"
                if dash_pid and dash_pid != "0":
                    dash_mask = subprocess.check_output(["taskset", "-p", dash_pid], text=True).strip().split(":")[-1].strip()

                keys_pid = subprocess.check_output(["systemctl", "show", "keys2mpv", "-p", "MainPID", "--value"], text=True).strip()
                keys_mask = "N/A"
                if keys_pid and keys_pid != "0":
                    keys_mask = subprocess.check_output(["taskset", "-p", keys_pid], text=True).strip().split(":")[-1].strip()

                ws_pid = subprocess.check_output(["systemctl", "show", "webserver", "-p", "MainPID", "--value"], text=True).strip()
                ws_mask = "N/A"
                if ws_pid and ws_pid != "0":
                    ws_mask = subprocess.check_output(["taskset", "-p", ws_pid], text=True).strip().split(":")[-1].strip()

                # Audio services (user systemd)
                pw_pid = subprocess.check_output(["systemctl", "--user", "show", "pipewire", "-p", "MainPID", "--value"], text=True).strip()
                pw_mask = "N/A"
                if pw_pid and pw_pid != "0":
                    pw_mask = subprocess.check_output(["taskset", "-p", pw_pid], text=True).strip().split(":")[-1].strip()

                wp_pid = subprocess.check_output(["systemctl", "--user", "show", "wireplumber", "-p", "MainPID", "--value"], text=True).strip()
                wp_mask = "N/A"
                if wp_pid and wp_pid != "0":
                    wp_mask = subprocess.check_output(["taskset", "-p", wp_pid], text=True).strip().split(":")[-1].strip()

                self.sj(200,{
                    "mpv": {"pid": mpv_pid, "mask": mpv_mask, "cores": mpv_cores},
                    "dashboard": {"pid": dash_pid, "mask": dash_mask, "cores": "0" if dash_mask=="1" else dash_mask},
                    "keys2mpv": {"pid": keys_pid, "mask": keys_mask, "cores": "0" if keys_mask=="1" else keys_mask},
                    "webserver": {"pid": ws_pid, "mask": ws_mask, "cores": "0" if ws_mask=="1" else ws_mask},
                    "pipewire": {"pid": pw_pid, "mask": pw_mask, "cores": "3" if pw_mask=="8" else pw_mask},
                    "wireplumber": {"pid": wp_pid, "mask": wp_mask, "cores": "3" if wp_mask=="8" else wp_mask},
                    "summary": {
                        "core0_background": ["dashboard", "keys2mpv", "webserver"],
                        "core1_2_media": ["mpv"],
                        "core3_audio": ["pipewire", "wireplumber"]
                    }
                })
            elif path=="/system/restart-mpv":
                stopped=mpv_stop()
                self.sj(200,{"ok":stopped.get("ok",False),"out":"mpv stopped (will restart on next play)","stop":stopped})
            elif path=="/system/restart-dashboard":
                r=subprocess.run(["sudo","systemctl","restart","dashboard@milhy777"],capture_output=True,text=True)  # nosec B603
                self.sj(200,{"ok":r.returncode==0,"returncode":r.returncode,"out":(r.stdout+r.stderr).strip()[:500] or "Dashboard restarting..."})
            elif path=="/system/restart-rpi":
                r=subprocess.run(["sudo","reboot"],capture_output=True,text=True)  # nosec B603
                self.sj(200,{"ok":r.returncode==0,"returncode":r.returncode,"out":(r.stdout+r.stderr).strip()[:500] or "Rebooting..."})
            elif path=="/system/reboot":
                r=subprocess.run(["sudo","reboot"],capture_output=True,text=True)
                self.sj(200,{"ok":r.returncode==0,"returncode":r.returncode,"out":(r.stdout+r.stderr).strip()[:500] or "Rebooting..."})
            else:
                handler = get_route(path)
                if handler:
                    return self.sj(200, handler(q))
                self.st(404,"nf","text/plain")
        except Exception as e: self.sj(500,{"error":str(e)})
    def do_POST(self):
        # IP allowlist check for POST requests
        if not _is_allowed_ip(self.client_address[0]):
            self.sj(403, {"error": "Forbidden – IP not allowed"})
            return
        # Rate limit check for POST requests
        if not _check_rate_limit(self.client_address[0]):
            self.send_error(429, "Rate limited")
            return
        ln=int(self.headers.get("Content-Length","0"))
        body=self.rfile.read(ln).decode()
        if self.path == "/wifi/connect":
            try:
                data = json.loads(body)
            except Exception:
                try:
                    data = {k: v[0] for k, v in parse_qs(body).items()}
                except Exception:
                    return self.st(400, "Invalid JSON or body", "text/plain")
            ssid = data.get("ssid", "").strip()
            password = data.get("password", "")
            return self.sj(200, wifi_connect(ssid, password))
        # Handle bug/feature reports submitted via POST /report
        if self.path == "/report":
            try:
                report=json.loads(body)
            except Exception:
                return self.st(400,"Invalid JSON", "text/plain")
            # Ensure required fields and validate type/description
            if not isinstance(report, dict) or report.get("type") not in ("bug", "feature") or not isinstance(report.get("description"), str) or not report["description"].strip():
                return self.st(400,"Missing or invalid required fields (type must be 'bug' or 'feature', description must be non-empty)", "text/plain")
            client_ip=self.client_address[0]
            filename=_save_report({**report, "timestamp": int(time.time())}, client_ip)
            return self.sj(201,{"ok":True,"file": filename})
        # Existing deprecated endpoint handling
        u=(parse_qs(body).get("url")or[""])[0].strip()
        if not u: return self.st(400,page())
        self.sj(410,{"ok":False,"deprecated":True,"error":"Kodi POST playback was removed; use /mpv/play or the Player tab."})

# WS_PORT is imported from config

async def term_handler(websocket):
    client_ip = websocket.remote_address[0] if websocket.remote_address else None
    if not client_ip or not _is_allowed_ip(client_ip):
        try:
            await websocket.close(1008, "Forbidden – IP not allowed")
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
        return
    session_name = "RPi:0"
    rows = 24
    cols = 80
    poll_task = None

    async def resize_tmux():
        try:
            proc = await asyncio.create_subprocess_exec("tmux", "resize-pane", "-t", session_name, "-x", str(cols), "-y", str(rows),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await asyncio.wait_for(proc.communicate(), timeout=1.0)
        except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)

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
                all_lines = content.splitlines()
                start = max(0, len(all_lines) - rows)
                lines = all_lines[start:]
                normalized = "\r\n".join(line[:cols] for line in lines)
                # tmux cursor_y is already relative to the visible pane, not scrollback.
                rel_y = max(0, min(rows - 1, cursor_y)) if all_lines else 0
                rel_x = max(0, min(cols - 1, cursor_x))
                await websocket.send(json.dumps({"output": normalized, "full": True, "cursor": {"x": rel_x, "y": rel_y}}))
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
                cols = max(40, min(220, int(data.get("cols") or cols)))
                await resize_tmux()
                if poll_task:
                    poll_task.cancel()
                poll_task = asyncio.create_task(poll_output())
            elif data.get("resize"):
                r = data.get("resize") or {}
                rows = max(10, min(80, int(r.get("rows") or rows)))
                cols = max(40, min(220, int(r.get("cols") or cols)))
                await resize_tmux()
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
                        proc = await asyncio.create_subprocess_exec("tmux", "send-keys", "-t", session_name, special_keys[inp],
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        await asyncio.wait_for(proc.communicate(), timeout=1.0)
                    else:
                        proc = await asyncio.create_subprocess_exec("tmux", "send-keys", "-t", session_name, "-l", inp,
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        await asyncio.wait_for(proc.communicate(), timeout=1.0)
                except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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

def _dashboard_hostnames_and_ips():
    names={"rpi-tv","rpi-tv.local","localhost"}
    ips={"127.0.0.1"}
    try:
        hn=socket.gethostname().strip()
        if hn:
            names.add(hn); names.add(f"{hn}.local")
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        for ip in subprocess.check_output(["hostname","-I"], text=True, timeout=2).split():
            if ip: ips.add(ip)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        for flag in ("-4","-6"):
            r=subprocess.run(["tailscale","ip",flag],capture_output=True,text=True,timeout=3)
            if r.returncode==0:
                for ip in r.stdout.split(): ips.add(ip)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        r=subprocess.run(["tailscale","status","--json"],capture_output=True,text=True,timeout=3)
        if r.returncode==0:
            d=json.loads(r.stdout or "{}")
            dns=(d.get("Self") or {}).get("DNSName") or ""
            if dns:
                names.add(dns.rstrip("."))
                names.add(dns.split(".")[0])
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return sorted(names), sorted(ips)

def _https_san():
    names, ips = _dashboard_hostnames_and_ips()
    return "subjectAltName=" + ",".join([*(f"DNS:{n}" for n in names), *(f"IP:{ip}" for ip in ips)])

def ensure_https_cert():
    os.makedirs(HTTPS_CERT_DIR, mode=0o700, exist_ok=True)
    san = _https_san()
    try:
        with open(HTTPS_SAN_FILE, "r", encoding="utf-8") as f:
            old_san = f.read().strip()
    except Exception:
        old_san = ""
    if os.path.exists(HTTPS_CERT_FILE) and os.path.exists(HTTPS_KEY_FILE) and old_san == san:
        return True, "existing"
    subj = "/CN=rpi-dashboard"
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-days", "825", "-nodes",
        "-keyout", HTTPS_KEY_FILE, "-out", HTTPS_CERT_FILE, "-subj", subj, "-addext", san,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "openssl failed")[:500]
    try:
        with open(HTTPS_SAN_FILE, "w", encoding="utf-8") as f: f.write(san + "\n")
        os.chmod(HTTPS_KEY_FILE, 0o600)
        os.chmod(HTTPS_CERT_FILE, 0o644)
        os.chmod(HTTPS_SAN_FILE, 0o644)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return True, "generated"

def start_http_server(port, label="HTTP"):
    if port == PORT:
        return None
    try:
        httpd=ThreadingHTTPServer((HOST, port), H)
    except Exception as e:
        print(f"[WARN] {label} disabled on port {port}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return None
    t=threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"RPi-TV {label} on http://{HOST}:{port}", flush=True)
    return httpd

def start_https_server(port=HTTPS_PORT, label="HTTPS"):
    ok, detail = ensure_https_cert()
    if not ok:
        print(f"[WARN] {label} disabled: {detail}", file=sys.stderr, flush=True)
        return None
    try:
        httpsd = ThreadingHTTPServer((HOST, port), H)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=HTTPS_CERT_FILE, keyfile=HTTPS_KEY_FILE)
        httpsd.socket = ctx.wrap_socket(httpsd.socket, server_side=True)
    except Exception as e:
        print(f"[WARN] {label} disabled on port {port}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return None
    t = threading.Thread(target=httpsd.serve_forever, daemon=True)
    t.start()
    print(f"RPi-TV {label} on https://{HOST}:{port} ({detail} cert)", flush=True)
    return httpsd

def mpv_ipc_query(command, path=MSOCK, quiet=True):
    """Send a JSON command to mpv IPC socket and return the parsed JSON response.
    Returns None on failure. Expected stale-socket errors stay quiet by default.
    """
    if not os.path.exists(path) or not stat.S_ISSOCK(os.stat(path).st_mode):
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(path)
        s.sendall((json.dumps(command) + "\n").encode('utf-8'))
        data = s.recv(SOCKET_RECV_SIZE)
        s.close()
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        if not quiet:
            print(f"[mpv_ipc_query] {type(e).__name__}: {e}", file=sys.stderr)
        return None

def mpv_ipc_socket_live(path=MSOCK):
    """Return True when an existing mpv IPC socket accepts commands.
    This protects active playback during webserver restarts. Never unlink a live mpv socket,
    otherwise the video may keep playing but WebUI loses control of it.
    """
    resp = mpv_ipc_query({"command": ["get_property", "pause"]}, path)
    return resp is not None and resp.get('error') in ('success', None)

def _playback_memory_file():
    return os.path.join(os.path.expanduser("~"), "rpi-dashboard", "playback-memory.json")

def _playback_media_key(url):
    m = YT_RE.search(url or "")
    if m:
        return m.group(1)
    import hashlib
    return hashlib.sha256((url or "").encode()).hexdigest()[:16]

def _load_playback_memory():
    mem_file = _playback_memory_file()
    try:
        if os.path.exists(mem_file):
            with open(mem_file, "r") as f:
                return json.load(f)
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {}

def _save_playback_memory(data):
    mem_file = _playback_memory_file()
    os.makedirs(os.path.dirname(mem_file), exist_ok=True)
    with open(mem_file, "w") as f:
        json.dump(data, f, indent=2)

def save_mpv_resume_memory():
    """Query mpv for playback position and metadata, return dict for persistence."""
    props = {}
    for prop in ("time-pos", "duration", "path", "media-title"):
        resp = mpv_ipc_query({"command": ["get_property", prop]})
        if resp and resp.get("error") in ("success", None):
            props[prop] = resp.get("data")
        else:
            props[prop] = None
    if props.get("time-pos") is None or props.get("duration") is None:
        return None
    position = float(props["time-pos"])
    duration = float(props["duration"])
    source_url = _murl or props.get("path") or ""
    video_id = _playback_media_key(source_url)
    if duration > 0 and (position >= duration * 0.95 or duration - position < 30):
        clear_mpv_memory_for_url(source_url)
        return None
    if position < 5:
        return None
    memory = {
        "id": video_id,
        "url": source_url,
        "title": props.get("media-title") or "",
        "position": position,
        "duration": duration,
        "updated_at": time.time(),
        "reason": "interrupted"
    }
    try:
        data = _load_playback_memory()
        data[video_id] = memory
        _save_playback_memory(data)
    except Exception as e:
        print(f"[save_mpv_resume_memory] failed to write memory: {e}", file=sys.stderr)
    return memory

def get_mpv_memory_for_url(url):
    """Return memory dict for given URL, or None."""
    return _load_playback_memory().get(_playback_media_key(url))

def clear_mpv_memory_for_url(url):
    """Remove memory entry for given URL. Returns True if cleared."""
    try:
        data = _load_playback_memory()
        video_id = _playback_media_key(url)
        if video_id in data:
            del data[video_id]
            _save_playback_memory(data)
            return True
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
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

# ── DLNA Input routing configuration and multi-output (Track 6 completion) ────────
def _dlnain_config_path():
    return os.path.expanduser("~/rpi-dashboard/.dlnain-config.json")

def _load_dlnain_config():
    path=_dlnain_config_path()
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"mode":"follow","manual_sinks":[],"multi_output":False}

def _save_dlnain_config(data):
    path=_dlnain_config_path()
    try:
        with open(path,"w") as f:
            json.dump(data,f,indent=2)
        return True
    except Exception:
        return False

def dlna_input_get_config():
    """Get DLNA Input routing configuration."""
    cfg=_load_dlnain_config()
    dst=_resolve_dlnain_target()
    running,src=_dlnain_loopback_running()
    active=sinks=[]
    if running:
        lb=_find_loopback_by_source(src)
        if lb:
            active=[lb["sink"]]
            sinks=[lb["sink"]]
    else:
        sinks=[dst] if dst else []
    return {
        "ok":True,
        "config":cfg,
        "running":running,
        "active_sinks":active,
        "default_target":dst,
        "stats":audio_state().get("dlna_connected", False)
    }

def dlna_input_status():
    """Get DLNA Input routing status."""
    cfg=_load_dlnain_config()
    dst=_resolve_dlnain_target()
    gmrender_src=None
    try:
        r=_run(["pactl","list","short","sources"])
        for l in r.stdout.splitlines():
            if "gmediarender" in l.lower():
                gmrender_src=l.split()[0]
                break
    except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    running,sink=_dlnain_loopback_running()
    active=[]
    if running and sink:
        active=[sink]
    sinks=[s for s in _pactl_lines("sinks") if any(k in s["name"] for k in ["hdmi","bluez","alsa_output"])]
    # Build label for DLNA Input card
    mode_label="Auto (follow primary)" if cfg.get("mode")=="follow" else "Manual (select outputs)"
    return {
        "ok":True,
        "configured":True,
        "mode":cfg.get("mode"),
        "manual_targets":cfg.get("manual_sinks",[]),
        "multi_output":cfg.get("multi_output",False),
        "active":running,
        "source_stream":gmrender_src or "gmrender-not-found",
        "target_stream":dst,
        "connectable_sinks":[s["name"] for s in sinks],
        "status_slot":{"mode":mode_label}
    }

def start_resume_poller():
    """Background thread to periodically save playback position while mpv is alive."""
    def _poller():
        while True:
            time.sleep(5.0)  # poll every 5 seconds
            try:
                if mpv_ipc_socket_live():
                    save_mpv_resume_memory()
            except Exception as e: print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)  # keep thread alive
    t = threading.Thread(target=_poller, daemon=True)
    t.start()

if __name__=="__main__":
    cleanup_stale_mpv_socket()
    start_ws_server()
    start_resume_poller()
    start_http_server(HTTP_PORT, "friendly HTTP")
    start_https_server(HTTPS_PORT, "HTTPS")
    if HTTPS_PORT_ALT != HTTPS_PORT:
        start_https_server(HTTPS_PORT_ALT, "friendly HTTPS")
    httpd=ThreadingHTTPServer((HOST,PORT),H)
    print(f"RPi-TV HTTP on http://{HOST}:{PORT}",flush=True)
    httpd.serve_forever()
