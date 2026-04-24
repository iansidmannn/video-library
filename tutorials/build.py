import json, os, re, subprocess, sys, time, urllib.request

GOOD_URLS = [
    # original 10 (ZP8gg... short URLs)
    'https://www.tiktok.com/t/ZP8gg5wV6/',
    'https://www.tiktok.com/t/ZP8ggFKko/',
    'https://www.tiktok.com/t/ZP8ggBkt7/',
    'https://www.tiktok.com/t/ZP8ggUE3A/',
    'https://www.tiktok.com/t/ZP8ggYxLa/',
    'https://www.tiktok.com/t/ZP8ggrPGT/',
    'https://www.tiktok.com/t/ZP8gghnf6/',
    'https://www.tiktok.com/t/ZP8ggm5vA/',
    'https://www.tiktok.com/t/ZP8ggAgqd/',
    'https://www.tiktok.com/t/ZP8ggkyNj/',
    # new additions
    'https://www.tiktok.com/@tiwald.leslee/video/7631772138868968717',
]

SHIT_URLS = [
    'https://www.tiktok.com/@mia3654184/video/7631584572194573599',
    'https://www.tiktok.com/@mia3654184/video/7631208437140983070',
    'https://www.tiktok.com/@tiwald.leslee/video/7632350144599428366',
    'https://www.tiktok.com/@tiwald.leslee/video/7632296395772382477',
    'https://www.tiktok.com/@tiwald.leslee/video/7632260599199599886',
    'https://www.tiktok.com/@tiwald.leslee/video/7632128889082400013',
    'https://www.tiktok.com/@tiwald.leslee/video/7631360650995911950',
    'https://www.tiktok.com/@tiwald.leslee/video/7631236714220031246',
    'https://www.tiktok.com/@tiwald.leslee/video/7630290572271570189',
    'https://www.tiktok.com/@tiwald.leslee/video/7629541787207601421',
    'https://www.tiktok.com/@aqjd87/video/7631355999810506006',
    'https://www.tiktok.com/@cuccia.chantal/video/7632353518933855519',
    'https://www.tiktok.com/@cuccia.chantal/video/7632134516643089695',
    'https://www.tiktok.com/@cuccia.chantal/video/7631590752962759967',
    'https://www.tiktok.com/@cuccia.chantal/video/7630646090651405598',
    'https://www.tiktok.com/@cuccia.chantal/video/7629493379239316767',
    'https://www.tiktok.com/@cuccia.chantal/video/7628237456097168671',
]

ROOT = r'C:\Users\feedp\Downloads\video-library-2'
DST_HTML = os.path.join(ROOT, 'index.html')
VDIR = os.path.join(ROOT, 'videos')
TDIR = os.path.join(ROOT, 'images', 'thumbs')
os.makedirs(VDIR, exist_ok=True)
os.makedirs(TDIR, exist_ok=True)

def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', s or 'unknown')

def fetch_meta(url, attempts=3):
    for attempt in range(1, attempts + 1):
        r = subprocess.run(
            ['python', '-m', 'yt_dlp', '--dump-json', '--no-playlist',
             '--skip-download', '--retries', '3', '--socket-timeout', '30', url],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode == 0:
            for ln in r.stdout.splitlines():
                if ln.startswith('{'):
                    try: return json.loads(ln)
                    except Exception: pass
        if attempt < attempts:
            print(f'  meta attempt {attempt} failed, retrying...')
            time.sleep(3)
        else:
            print(f'  meta stderr: {r.stderr.strip()[:200]}')
    return None

def download_video(url, uploader, vid_id):
    fname = f'{safe_name(uploader)}_{vid_id}.mp4'
    out = os.path.join(VDIR, fname)
    if os.path.exists(out):
        return fname
    subprocess.run(
        ['python', '-m', 'yt_dlp', '-o', out, '--no-playlist', '--quiet', '--no-warnings', url],
        capture_output=True, text=True)
    return fname if os.path.exists(out) else None

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
def fetch_saves(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'replace')
        m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([\s\S]*?)</script>', html)
        if not m: return 0
        d = json.loads(m.group(1))
        it = d.get('__DEFAULT_SCOPE__', {}).get('webapp.video-detail', {}).get('itemInfo', {}).get('itemStruct', {})
        sv2 = it.get('statsV2', {}) or {}
        s = it.get('stats', {}) or {}
        return int(sv2.get('collectCount') or s.get('collectCount') or 0)
    except Exception as e:
        print(f'  saves fetch err: {e}')
        return 0

def make_thumb(fname, vid_id):
    src = os.path.join(VDIR, fname)
    out = os.path.join(TDIR, f'{vid_id}.jpg')
    if os.path.exists(out): return True
    subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-ss', '0.5', '-i', src, '-frames:v', '1',
         '-vf', 'scale=480:-2', '-q:v', '4', out],
        capture_output=True, text=True)
    return os.path.exists(out)

def process(urls, tag):
    out = []
    seen = set()
    for i, url in enumerate(urls, 1):
        print(f'[{tag} {i}/{len(urls)}] {url}')
        meta = fetch_meta(url)
        if not meta:
            print('  meta failed, skip'); continue
        vid_id = meta['id']
        if vid_id in seen:
            print('  duplicate, skip'); continue
        uploader = meta.get('uploader') or 'unknown'
        fname = download_video(url, uploader, vid_id)
        if not fname:
            print('  download failed, skip'); continue
        if not make_thumb(fname, vid_id):
            print('  thumb failed, skip'); continue
        canonical = f'https://www.tiktok.com/@{uploader}/video/{vid_id}'
        saves = fetch_saves(canonical)
        out.append({
            'id': vid_id,
            'uploader': uploader,
            'views': int(meta.get('view_count') or 0),
            'likes': int(meta.get('like_count') or 0),
            'comments': int(meta.get('comment_count') or 0),
            'shares': int(meta.get('repost_count') or 0),
            'saves': saves,
            'duration': int(meta.get('duration') or 0),
            'thumbnail': f'images/thumbs/{vid_id}.jpg',
            'url': canonical,
            'file': f'videos/{fname}',
            'tag': tag,
        })
        seen.add(vid_id)
        print(f'  OK {meta.get("view_count",0):,} views, {saves:,} saves')
    return out

records = []
records += process(GOOD_URLS, 'Good')
records += process(SHIT_URLS, 'Shit')
records.sort(key=lambda r: -r['views'])

good_n = sum(1 for r in records if r['tag'] == 'Good')
shit_n = sum(1 for r in records if r['tag'] == 'Shit')
print(f'\n{len(records)} videos total — Good:{good_n} Shit:{shit_n}')

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Library</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#111;color:#e8e8e8;font-family:'Inter',system-ui,sans-serif;min-height:100vh}
.hdr{padding:16px 12px 12px;position:sticky;top:0;z-index:50;background:#111;border-bottom:1px solid #2a2a2a}
h1{font-size:18px;font-weight:800;text-align:center;margin-bottom:12px}
h1 span{color:#1DB954}
.tabs{display:flex;gap:8px;justify-content:center}
.tab{padding:8px 22px;border:1px solid #2a2a2a;background:transparent;color:#999;font-size:13px;font-weight:700;cursor:pointer;border-radius:8px;transition:all .2s;font-family:inherit}
.tab.active{background:#1DB954;color:#000;border-color:#1DB954}
.tab .cnt{font-size:11px;font-weight:600;opacity:.6;margin-left:4px}
.tab.active .cnt{opacity:.7}
.sorts{display:flex;gap:6px;justify-content:center;margin-top:10px;overflow-x:auto;scrollbar-width:none;padding:0 8px}
.sorts::-webkit-scrollbar{display:none}
.sort{padding:5px 11px;border-radius:7px;border:1px solid #2a2a2a;background:transparent;color:#999;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap;font-family:inherit;transition:all .15s}
.sort.active{background:rgba(29,185,84,.12);color:#1DB954;border-color:#178a40}
.sort .arr{font-size:9px;margin-left:3px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-width:1200px;margin:0 auto;padding:12px}
@media(min-width:600px){.grid{grid-template-columns:repeat(4,1fr);gap:10px}}
@media(min-width:900px){.grid{grid-template-columns:repeat(5,1fr)}}
@media(min-width:1200px){.grid{grid-template-columns:repeat(6,1fr)}}
.card{position:relative;aspect-ratio:9/16;border-radius:8px;overflow:hidden;background:#1c1c1c;border:1px solid #2a2a2a;cursor:pointer;transition:transform .15s}
.card:hover{transform:translateY(-2px);border-color:#444}
.card img,.card video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000}
.card .grad{position:absolute;inset:0;background:linear-gradient(transparent 45%,rgba(0,0,0,.85) 90%);pointer-events:none}
.card .views{position:absolute;bottom:18px;left:6px;font-size:13px;font-weight:800;color:#1DB954;text-shadow:0 1px 4px rgba(0,0,0,.9);z-index:2}
.card .user{position:absolute;bottom:4px;left:6px;right:6px;font-size:10px;font-weight:600;color:rgba(255,255,255,.75);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 4px rgba(0,0,0,.8);z-index:2}
.card .dur{position:absolute;top:5px;right:5px;background:rgba(0,0,0,.6);padding:2px 5px;border-radius:4px;font-size:9px;font-weight:600;color:rgba(255,255,255,.85);z-index:2}
.card .play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:38px;height:38px;border-radius:50%;background:rgba(0,0,0,.55);border:1.5px solid rgba(255,255,255,.85);display:flex;align-items:center;justify-content:center;z-index:3;transition:opacity .15s,background .15s;pointer-events:none}
.card.playing .play{opacity:0}
.card:hover .play{background:#1DB954;border-color:#1DB954}
.card .play::after{content:'';width:0;height:0;border-left:11px solid #fff;border-top:7px solid transparent;border-bottom:7px solid transparent;margin-left:3px}
.card:hover .play::after{border-left-color:#000}
.empty{grid-column:1/-1;text-align:center;color:#666;font-size:14px;padding:60px 20px}
</style>
</head>
<body>
<div class="hdr">
  <h1>Video <span>Library</span></h1>
  <div class="tabs">
    <button class="tab active" data-tag="Good">Good <span class="cnt" id="cnt-Good">0</span></button>
    <button class="tab" data-tag="Shit">Shit <span class="cnt" id="cnt-Shit">0</span></button>
  </div>
  <div class="sorts" id="sorts"></div>
</div>
<div class="grid" id="grid"></div>
<script>
const V=__DATA__;
const fmt=n=>n>=1e6?(n/1e6).toFixed(1).replace(/\\.0$/,'')+'M':n>=1e3?(n/1e3).toFixed(1).replace(/\\.0$/,'')+'K':n+'';
const dur=s=>Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
const g=document.getElementById('grid');
let cur='Good';
const SORTS=[{k:'views',l:'Views'},{k:'likes',l:'Likes'},{k:'saves',l:'Saves'},{k:'shares',l:'Shares'},{k:'comments',l:'Comments'},{k:'duration',l:'Length'}];
let sortK='views',sortDir=-1;

document.getElementById('cnt-Good').textContent=V.filter(v=>v.tag==='Good').length;
document.getElementById('cnt-Shit').textContent=V.filter(v=>v.tag==='Shit').length;

const sortRow=document.getElementById('sorts');
SORTS.forEach(s=>{
  const b=document.createElement('button');b.className='sort';b.dataset.k=s.k;
  b.textContent=s.l;
  if(s.k===sortK){b.classList.add('active');b.innerHTML=s.l+' <span class="arr">'+(sortDir===-1?'▼':'▲')+'</span>';}
  b.onclick=()=>{
    if(sortK===s.k)sortDir=-sortDir;else{sortK=s.k;sortDir=-1;}
    sortRow.querySelectorAll('.sort').forEach(x=>{
      x.classList.remove('active');
      const key=x.dataset.k,lbl=SORTS.find(q=>q.k===key).l;
      x.innerHTML=key===sortK?lbl+' <span class="arr">'+(sortDir===-1?'▼':'▲')+'</span>':lbl;
      if(key===sortK)x.classList.add('active');
    });
    render();
  };
  sortRow.appendChild(b);
});

function makeCard(v){
  const c=document.createElement('div');c.className='card';
  c.innerHTML=`
    <img src="${v.thumbnail}" loading="lazy" alt="">
    <div class="grad"></div>
    <div class="dur">${dur(v.duration)}</div>
    <div class="views">${fmt(v.views)}</div>
    <div class="user">@${v.uploader}</div>
    <div class="play"></div>`;
  c.onclick=()=>toggle(c,v);
  return c;
}
function toggle(card,v){
  let video=card.querySelector('video');
  if(!video){
    video=document.createElement('video');
    video.src=v.file;video.playsInline=true;video.controls=false;video.loop=true;
    card.insertBefore(video,card.querySelector('.grad'));
    video.addEventListener('click',e=>{e.stopPropagation();video.paused?video.play():video.pause()});
  }
  if(video.paused){
    document.querySelectorAll('.card.playing').forEach(c=>{const ov=c.querySelector('video');if(ov){ov.pause();c.classList.remove('playing')}});
    video.play();card.classList.add('playing');
  } else {
    video.pause();card.classList.remove('playing');
  }
}
function render(){
  document.querySelectorAll('.card.playing video').forEach(v=>v.pause());
  g.innerHTML='';
  const list=V.filter(v=>v.tag===cur).slice().sort((a,b)=>sortDir*((a[sortK]||0)-(b[sortK]||0)));
  if(list.length===0){
    g.innerHTML='<div class="empty">no videos yet</div>';
    return;
  }
  list.forEach(v=>g.appendChild(makeCard(v)));
}
document.querySelectorAll('.tab').forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    cur=t.dataset.tag;
    render();
  };
});
render();
</script>
</body>
</html>
'''

html_out = HTML.replace('__DATA__', json.dumps(records, ensure_ascii=False))
with open(DST_HTML, 'w', encoding='utf-8') as f:
    f.write(html_out)
print(f'\nwrote {DST_HTML}')
