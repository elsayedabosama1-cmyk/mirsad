#!/usr/bin/env python3
"""يجيب آخر منشورات صفحتي مرصد وBy the Way من فيسبوك ويكتبها في data/fb_pages.json
عشان قسم «شاشات العلامات» في الموقع يعرض البوستات الحقيقية.

الصور بتتحفظ جوه المستودع (photos/fb) عشان روابط فيسبوك المؤقتة تبقى مشكلة،
والملفات القديمة بتتشال لما البوست يخرج من القائمة.

التوكن: متغير البيئة FB_TOKEN (توكن مستخدم طويل الأمد). السكربت بيستخرج توكن كل صفحة
من /me/accounts، فمش محتاج توكنات صفحات منفصلة.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

GRAPH = 'https://graph.facebook.com/v21.0'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'fb_pages.json')
IMG_DIR = os.path.join(ROOT, 'photos', 'fb')
IMG_REL = 'photos/fb'
PAGES = [('mirsad', '1475210439010063', 'مرصد'), ('btw', '111570231877045', 'By the Way'),
         ('radar', '1492208437299343', 'رادار مصر')]
LIMIT = '8'


def get(path, params):
    url = f'{GRAPH}/{path}?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            body = ''
            try:
                body = e.read().decode('utf-8')[:300]
            except Exception:
                pass
            if attempt == 2:
                raise SystemExit(f'Graph API error on {path}: {e} {body}')
            time.sleep(3 * (attempt + 1))


def safe(name):
    return re.sub(r'[^A-Za-z0-9_-]', '', str(name))[:80]


def download(url, dest):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=45) as r:
            blob = r.read()
        if len(blob) < 1000:
            return False
        with open(dest, 'wb') as f:
            f.write(blob)
        return True
    except Exception as e:
        print(f'image failed {url[:60]}: {e}')
        return False


def main():
    token = os.environ.get('FB_TOKEN', '').strip()
    if not token:
        raise SystemExit('FB_TOKEN is not set')

    acc = get('me/accounts', {'fields': 'id,name,access_token', 'limit': '100', 'access_token': token})
    by_id = {p['id']: p for p in acc.get('data', [])}

    os.makedirs(IMG_DIR, exist_ok=True)
    keep = set()
    pages = {}
    for slug, pid, name in PAGES:
        page_token = (by_id.get(pid) or {}).get('access_token') or token
        res = get(f'{pid}/posts', {
            'fields': 'id,message,created_time,permalink_url,full_picture',
            'limit': LIMIT,
            'access_token': page_token,
        })
        posts = []
        for p in res.get('data', []):
            msg = (p.get('message') or '').strip()
            if not msg and not p.get('full_picture'):
                continue
            try:
                at = int(time.mktime(time.strptime(p['created_time'], '%Y-%m-%dT%H:%M:%S%z')) * 1000)
            except Exception:
                at = 0
            img = ''
            pic = p.get('full_picture', '')
            if pic:
                fn = safe(p['id']) + '.jpg'
                dest = os.path.join(IMG_DIR, fn)
                if os.path.exists(dest) or download(pic, dest):
                    img = f'{IMG_REL}/{fn}'
                    keep.add(fn)
                else:
                    img = pic
            posts.append({
                'id': p['id'],
                't': msg.split('\n')[0].strip()[:120],
                'b': msg,
                'img': img,
                'at': at,
                'url': p.get('permalink_url', ''),
            })
        pages[slug] = {'id': pid, 'name': name, 'posts': posts}
        print(f'{slug}: {len(posts)} posts')

    removed = 0
    for f in os.listdir(IMG_DIR):
        if f not in keep:
            os.remove(os.path.join(IMG_DIR, f))
            removed += 1

    data = {'version': 1, 'updated': int(time.time() * 1000), 'pages': pages}
    old = ''
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as fh:
            old = fh.read()
    if old:
        try:
            o = json.loads(old)
            if json.dumps(o.get('pages'), ensure_ascii=False, sort_keys=True) == json.dumps(pages, ensure_ascii=False, sort_keys=True) and not removed:
                print('no change')
                return
        except Exception:
            pass
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    print('wrote', OUT, 'images removed', removed)


if __name__ == '__main__':
    main()
