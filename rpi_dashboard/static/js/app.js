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
async function routesRefresh(){let[alexa,_,dlnain]=await Promise.all([api('/audio/route/alexa-bt?action=status'),api('/dlna/renderer/status').catch(()=>({})),api('/audio/route/dlna-input/status').catch(()=>({}))]);dlnain=dlnain||{};let el=$('#ta-routes');if(!el)return;let h='';let alexaOn=alexa.on;let alexaTarget=alexa.target||'?';let alexaDefault=alexa.default_sink||'?';
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
h+='<div class="media-card route-card '+(getCookie('multi-output')==='true'?'on':'off')+'"><h4>🔀 Multi-Output</h4>';
h+='<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">'+badge(getCookie('multi-output')==='true','ACTIVE')+' Route same source to multiple outputs simultaneously.</div>';
h+='<button data-act="multi-toggle" class="'+(getCookie('multi-output')==='true' ? 'danger':'')+'">'+(getCookie('multi-output')==='true'?'Turn OFF Multi-Output':'Turn ON Multi-Output')+'</button>';
h+='</div>';

// Update SVG connections when multi-output changes
function updateAudioPaths(){ routesRefresh(); redraw(); }
el.innerHTML=h;el.onclick=function(e){let b=e.target.closest('[data-act]');if(!b)return;let a=b.dataset.act;if(a==='alexa-start')alexaRouteStart();else if(a==='alexa-stop')alexaRouteStop();else if(a==='alexa-retarget')alexaRouteRetarget();else if(a==='dlnain-start')dlnainStart();else if(a==='dlnain-stop')dlnainStop();else if(a==='dlnain-mode')dlnainMode(b.dataset.mode);else if(a==='dlnain-target')dlnainTarget(b.dataset.sink);else if(a==='multi-toggle')multiOutputToggle()}}
function multiOutputToggle(){let on=getCookie('multi-output')==='true';setCookie('multi-output',on?'false':'true');msg(on?'Multi-output disabled':'Multi-output enabled','info');routesRefresh()}
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
function renderBtDevices(devs){if(!devs||!devs.length)return '<div>No Bluetooth devices listed.</div>';return devs.map(d=>'<div class="media-card" style="min-height:70px;margin:.3rem 0"><h4>'+devIcon(d.kind)+' '+esc(d.name||'Unknown')+' '+badge(!!d.connected,d.connected?'CONNECTED':(d.paired?'PAIRED':'FOUND'))+'</h4><div class="media-meta">MAC: '+esc(d.mac)+'<br>Role: '+esc(d.kind||'unknown')+' · Trusted: '+(d.trusted?'yes':'no')+'</div><div class="row" style="margin-top:.35rem"><button data-i18n="pair" onclick="btPair(\''+jsarg(d.mac)+'\')">Pair</button><button data-i18n="connect" onclick="btConnect(\''+jsarg(d.mac)+'\')">Connect</button><button data-i18n="trust" onclick="btTrust(\''+jsarg(d.mac)+'\')">Trust</button><button class="danger" data-i18n="remove" onclick="btRemove(\''+jsarg(d.mac)+'\')">Remove</button></div></div>').join('')}
async function devicesRefresh(){let r=await api('/devices/state');if(r.error){msg(r.error,'err');return}$('#dev-bt-list').innerHTML=renderBtDevices((r.bluetooth&&r.bluetooth.paired)||[]);$('#dev-bt-status').textContent=((r.bluetooth&&r.bluetooth.paired)||[]).length+' paired'}
async function deviceBtScan(){msg(L('scan')+' Bluetooth...','info');let r=await api('/devices/bt/scan?seconds=6');let all=[...(r.paired||[]),...(r.devices||[])];$('#dev-bt-list').innerHTML=renderBtDevices(all);$('#dev-bt-status').textContent=(r.devices||[]).length+' '+L('found')+', '+(r.paired||[]).length+' '+L('paired');msg(L('scan')+' Bluetooth done','ok')}
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

// Theme System
const ThemeManager = {
    themes: ['dark', 'light'],
    accents: ['blue', 'green', 'purple', 'orange', 'pink'],
    currentTheme: localStorage.getItem('theme') || 'dark',
    currentAccent: localStorage.getItem('accent') || 'blue',
    
    init() {
        this.applyTheme(this.currentTheme);
        this.applyAccent(this.currentAccent);
        
        // Detect system preference
        if (!localStorage.getItem('theme')) {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.setTheme(prefersDark ? 'dark' : 'light');
        }
    },
    
    setTheme(theme) {
        if (!this.themes.includes(theme)) return;
        this.currentTheme = theme;
        localStorage.setItem('theme', theme);
        this.applyTheme(theme);
    },
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    },
    
    setAccent(accent) {
        if (!this.accents.includes(accent)) return;
        this.currentAccent = accent;
        localStorage.setItem('accent', accent);
        this.applyAccent(accent);
    },
    
    applyAccent(accent) {
        document.documentElement.setAttribute('data-accent', accent);
    },
    
    toggle() {
        this.setTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }
};

// Initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});

// Add theme toggle to topbar
function addThemeToggle() {
    const topbar = document.getElementById('topbar');
    if (!topbar) return;
    
    const themeBtn = document.createElement('button');
    themeBtn.className = 'lang-btn';
    themeBtn.title = 'Toggle theme';
    themeBtn.setAttribute('aria-label', 'Toggle theme');
    themeBtn.innerHTML = '🌓';
    themeBtn.onclick = () => ThemeManager.toggle();
    themeBtn.style.cssText = 'font-size:.78rem;padding:.22rem .42rem;border-radius:999px;border:1px solid #30363d;background:#161b22;color:#c9d1d9;cursor:pointer';
    
    const langSwitch = document.getElementById('lang-switch');
    if (langSwitch) {
        langSwitch.parentNode.insertBefore(themeBtn, langSwitch);
    }
}

// Call on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addThemeToggle);
} else {
    addThemeToggle();
}
