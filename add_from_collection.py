import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, 'index.html')
VDIR = os.path.join(ROOT, 'videos')
TDIR = os.path.join(ROOT, 'images', 'thumbs')
os.makedirs(VDIR, exist_ok=True)
os.makedirs(TDIR, exist_ok=True)

COLLECTION_URL = "https://www.tiktok.com/@trypinatafarms/collection/Newpranks-7623916431533148958"

# uploader substring -> category override (lowercase match)
CATEGORY_OVERRIDES = {
    'tiwald': 'Compilations',
}
DEFAULT_CATEGORY = 'Pranks'
DEFAULT_SUBCAT = 'New Pranks'
COMP_SUBCAT = 'Compilations'

def load_existing():
    with open(HTML, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith('const V = ['):
            idx = i
            break
    else:
        sys.exit('could not find const V line')
    line = lines[idx]
    prefix = line[:line.index('[')]
    end = line.rindex(']') + 1
    suffix = line[end:]
    arr = json.loads(line[line.index('['):end])
    return lines, idx, prefix, suffix, arr

def fetch_collection():
    print('fetching collection listing...')
    r = subprocess.run(
        ['python', '-m', 'yt_dlp', '--flat-playlist', '--dump-json', COLLECTION_URL],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    entries = []
    for ln in r.stdout.splitlines():
        if ln.startswith('{'):
            try: entries.append(json.loads(ln))
            except: pass
    print(f'  got {len(entries)} entries')
    return entries

def pick_category(uploader):
    u = (uploader or '').lower()
    for key, cat in CATEGORY_OVERRIDES.items():
        if key in u:
            return cat
    return DEFAULT_CATEGORY

def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', s or 'unknown')

def download_video(url, uploader, vid_id):
    fname = f'{safe_name(uploader)}_{vid_id}.mp4'
    out = os.path.join(VDIR, fname)
    if os.path.exists(out):
        return fname
    print(f'  downloading {fname}...')
    r = subprocess.run(
        ['python', '-m', 'yt_dlp', '-o', out,
         '--no-playlist', '--quiet', '--no-warnings', url],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print(f'  FAIL: {r.stderr.strip()[:200]}')
        return None
    return fname

def make_thumb(fname, vid_id):
    src = os.path.join(VDIR, fname)
    out = os.path.join(TDIR, f'{vid_id}.jpg')
    if os.path.exists(out): return True
    r = subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error',
         '-ss', '0.5', '-i', src, '-frames:v', '1',
         '-vf', 'scale=480:-2', '-q:v', '4', out],
        capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(out)

def to_record(entry, fname):
    vid_id = entry['id']
    uploader = entry.get('uploader') or 'unknown'
    cat = pick_category(uploader)
    subcat = COMP_SUBCAT if cat == 'Compilations' else DEFAULT_SUBCAT
    return {
        'id': vid_id,
        'uploader': uploader,
        'views': int(entry.get('view_count') or 0),
        'likes': int(entry.get('like_count') or 0),
        'comments': int(entry.get('comment_count') or 0),
        'shares': int(entry.get('repost_count') or 0),
        'duration': int(entry.get('duration') or 0),
        'description': entry.get('description') or entry.get('title') or '',
        'thumbnail': f'images/thumbs/{vid_id}.jpg',
        'url': f'https://www.tiktok.com/@{uploader}/video/{vid_id}',
        'file': fname,
        'categories': [subcat],
        'category': cat,
    }

def main():
    lines, idx, prefix, suffix, arr = load_existing()
    existing_ids = {v['id'] for v in arr}
    print(f'library has {len(existing_ids)} videos')

    entries = fetch_collection()
    to_add = [e for e in entries if e['id'] not in existing_ids]
    print(f'new videos to add: {len(to_add)}')
    for e in to_add:
        print(f'  {e["id"]} | {e.get("uploader")} | {e.get("view_count",0):,} views')

    added = []
    for e in to_add:
        vid_id = e['id']
        uploader = e.get('uploader') or 'unknown'
        url = e.get('url') or f'https://www.tiktok.com/@{uploader}/video/{vid_id}'
        fname = download_video(url, uploader, vid_id)
        if not fname:
            print(f'  skip {vid_id}: download failed')
            continue
        if not make_thumb(fname, vid_id):
            print(f'  skip {vid_id}: thumb failed')
            continue
        rec = to_record(e, fname)
        arr.append(rec)
        added.append(rec)
        print(f'  added {rec["uploader"]} [{rec["category"]}] {rec["views"]:,} views')

    if not added:
        print('no new entries added')
        return

    new_line = prefix + json.dumps(arr, ensure_ascii=False, separators=(', ', ': ')) + suffix
    lines[idx] = new_line
    with open(HTML, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f'updated index.html (+{len(added)} entries, total {len(arr)})')

if __name__ == '__main__':
    main()
