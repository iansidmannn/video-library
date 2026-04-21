import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, 'index.html')
VDIR = os.path.join(ROOT, 'videos')
TDIR = os.path.join(ROOT, 'images', 'thumbs')

# user-provided IG compilations
# shortcode: views (from IG insights; yt-dlp can't fetch plays without login)
IG_ITEMS = [
    ('DXMMze_k7bm', 780216),
    ('DWkfSt8jNVy', 103),
    ('DXH_ABRDbIW', 86962),
    ('DXFV8zyjd2S', 370299),
    ('DXNCocRiNHx', 4448),
    ('DXKNQBQCQNS', 6973),
    ('DXFboikT_f-', 18362),
    ('DW1suKOiF_l', 12058),
]

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

def safe_name(s):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', s or 'unknown')

def fetch_meta(url):
    r = subprocess.run(
        ['python', '-m', 'yt_dlp', '--dump-json', '--no-playlist', '--skip-download', url],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    for ln in r.stdout.splitlines():
        if ln.startswith('{'):
            try: return json.loads(ln)
            except: pass
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
        print(f'    FAIL: {r.stderr.strip()[:200]}')
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
    return os.path.exists(out)

def main():
    lines, idx, prefix, suffix, arr = load_existing()
    existing_ids = {v['id'] for v in arr}
    print(f'library has {len(existing_ids)} videos')

    to_process = [(sc, v) for sc, v in IG_ITEMS if sc not in existing_ids]
    skipped = [sc for sc, _ in IG_ITEMS if sc in existing_ids]
    print(f'already in library: {skipped}')
    print(f'new to add: {len(to_process)}')

    added = []
    for shortcode, views in to_process:
        print(f'\n[{shortcode}] fetching metadata...')
        url = f'https://www.instagram.com/p/{shortcode}/'
        meta = fetch_meta(url)
        if not meta:
            print(f'  meta fetch failed, skipping')
            continue
        uploader = meta.get('channel') or meta.get('uploader_id') or 'unknown'
        print(f'  uploader={uploader}, likes={meta.get("like_count",0)}, duration={meta.get("duration",0)}')
        print(f'  downloading...')
        fname = download_video(url, uploader, shortcode)
        if not fname:
            print(f'  download failed, skipping')
            continue
        if not make_thumb(fname, shortcode):
            print(f'  thumb failed, skipping')
            continue
        rec = {
            'id': shortcode,
            'uploader': uploader,
            'views': int(views),
            'likes': int(meta.get('like_count') or 0),
            'comments': int(meta.get('comment_count') or 0),
            'shares': 0,
            'duration': int(meta.get('duration') or 0),
            'description': meta.get('description') or meta.get('title') or '',
            'thumbnail': f'images/thumbs/{shortcode}.jpg',
            'url': url,
            'file': fname,
            'categories': ['Compilations'],
            'category': 'Compilations',
        }
        arr.append(rec)
        added.append(rec)
        print(f'  added as Compilation: {views:,} views, {rec["likes"]:,} likes, {rec["comments"]:,} comments')

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
