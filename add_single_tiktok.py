"""Add a single TikTok video by URL. Reuses logic from add_from_collection.py.

Usage: python add_single_tiktok.py <url> [<url> ...]
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, 'index.html')
VDIR = os.path.join(ROOT, 'videos')
TDIR = os.path.join(ROOT, 'images', 'thumbs')

CATEGORY_OVERRIDES = {'tiwald': 'Compilations'}
DEFAULT_CATEGORY = 'Pranks'
DEFAULT_SUBCAT = 'New Pranks'
COMP_SUBCAT = 'Compilations'

def load_existing():
    with open(HTML, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith('const V = ['):
            idx = i; break
    else:
        sys.exit('could not find const V line')
    line = lines[idx]
    prefix = line[:line.index('[')]
    end = line.rindex(']') + 1
    return lines, idx, prefix, line[end:], json.loads(line[line.index('['):end])

def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', s or 'unknown')

def pick_category(uploader):
    u = (uploader or '').lower()
    for key, cat in CATEGORY_OVERRIDES.items():
        if key in u:
            return cat
    return DEFAULT_CATEGORY

def fetch_meta(url):
    r = subprocess.run(
        ['python', '-m', 'yt_dlp', '--dump-json', '--no-playlist', '--skip-download', url],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    for ln in r.stdout.splitlines():
        if ln.startswith('{'):
            try: return json.loads(ln)
            except: pass
    print(f'  meta fetch FAIL: {r.stderr.strip()[:200]}')
    return None

def download_video(url, uploader, vid_id):
    fname = f'{safe_name(uploader)}_{vid_id}.mp4'
    out = os.path.join(VDIR, fname)
    if os.path.exists(out):
        return fname
    r = subprocess.run(
        ['python', '-m', 'yt_dlp', '-o', out,
         '--no-playlist', '--quiet', '--no-warnings', url],
        capture_output=True, text=True)
    if not os.path.exists(out):
        print(f'  download FAIL: {r.stderr.strip()[:200]}')
        return None
    return fname

def make_thumb(fname, vid_id):
    src = os.path.join(VDIR, fname)
    out = os.path.join(TDIR, f'{vid_id}.jpg')
    if os.path.exists(out): return True
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '0.5',
                    '-i', src, '-frames:v', '1', '-vf', 'scale=480:-2',
                    '-q:v', '4', out], capture_output=True)
    return os.path.exists(out)

def to_record(meta, fname):
    vid_id = meta['id']
    uploader = meta.get('uploader') or meta.get('channel') or 'unknown'
    cat = pick_category(uploader)
    subcat = COMP_SUBCAT if cat == 'Compilations' else DEFAULT_SUBCAT
    return {
        'id': vid_id,
        'uploader': uploader,
        'views': int(meta.get('view_count') or 0),
        'likes': int(meta.get('like_count') or 0),
        'comments': int(meta.get('comment_count') or 0),
        'shares': int(meta.get('repost_count') or 0),
        'duration': int(meta.get('duration') or 0),
        'description': meta.get('description') or meta.get('title') or '',
        'thumbnail': f'images/thumbs/{vid_id}.jpg',
        'url': meta.get('webpage_url') or f'https://www.tiktok.com/@{uploader}/video/{vid_id}',
        'file': fname,
        'categories': [subcat],
        'category': cat,
    }

def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python add_single_tiktok.py <url> [<url> ...]')
    urls = sys.argv[1:]
    lines, idx, prefix, suffix, arr = load_existing()
    existing_ids = {v['id'] for v in arr}
    print(f'library has {len(existing_ids)} videos')

    added = []
    for url in urls:
        print(f'\n[{url}]')
        meta = fetch_meta(url)
        if not meta:
            continue
        vid_id = meta['id']
        if vid_id in existing_ids:
            print(f'  already in library: {vid_id}')
            continue
        fname = download_video(url, meta.get('uploader') or 'unknown', vid_id)
        if not fname:
            continue
        if not make_thumb(fname, vid_id):
            print(f'  thumb failed')
            continue
        rec = to_record(meta, fname)
        arr.append(rec)
        added.append(rec)
        existing_ids.add(vid_id)
        print(f'  added {rec["uploader"]} [{rec["category"]}] {rec["views"]:,} views, {rec["likes"]:,} likes')

    if not added:
        print('\nno new entries added')
        return
    new_line = prefix + json.dumps(arr, ensure_ascii=False, separators=(', ', ': ')) + suffix
    lines[idx] = new_line
    with open(HTML, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f'\nupdated index.html (+{len(added)} entries, total {len(arr)})')

if __name__ == '__main__':
    main()
