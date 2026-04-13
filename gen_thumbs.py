import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, 'index.html')
VDIR = os.path.join(ROOT, 'videos')
TDIR = os.path.join(ROOT, 'images', 'thumbs')
os.makedirs(TDIR, exist_ok=True)

with open(HTML, 'r', encoding='utf-8') as f:
    lines = f.readlines()

data_line_idx = None
for i, ln in enumerate(lines):
    if ln.lstrip().startswith('const V = ['):
        data_line_idx = i
        break
if data_line_idx is None:
    sys.exit('Could not find const V = [ line')

line = lines[data_line_idx]
prefix = line[:line.index('[')]
suffix_start = line.rindex(']') + 1
suffix = line[suffix_start:]
arr = json.loads(line[line.index('['):suffix_start])

for v in arr:
    vid_id = v['id']
    src = os.path.join(VDIR, v['file'])
    out = os.path.join(TDIR, f'{vid_id}.jpg')
    rel = f'images/thumbs/{vid_id}.jpg'
    if not os.path.exists(out):
        if not os.path.exists(src):
            print(f'skip (no video): {v["file"]}')
            continue
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-ss', '0.5', '-i', src,
            '-frames:v', '1',
            '-vf', 'scale=480:-2',
            '-q:v', '4',
            out,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            print(f'fail {v["file"]}: {r.stderr.strip()[:200]}')
            continue
        print(f'made {rel}')
    v['thumbnail'] = rel

new_line = prefix + json.dumps(arr, ensure_ascii=False, separators=(', ', ': ')) + suffix
lines[data_line_idx] = new_line

with open(HTML, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'done: {len(arr)} entries, thumbs in {TDIR}')
