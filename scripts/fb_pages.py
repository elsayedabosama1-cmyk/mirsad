#!/usr/bin/env python3
"""يجيب آخر منشورات صفحتي مرصد وBy the Way من فيسبوك ويكتبها في data/fb_pages.json
عشان قسم «شاشات العلامات» في الموقع يعرض البوستات الحقيقية.

التوكن: متغير البيئة FB_TOKEN (توكن مستخدم طويل الأمد). السكربت بيستخرج توكن كل صفحة
من /me/accounts، فمش محتاج توكنات صفحات منفصلة.
"""
import json, os, sys, time, urllib.parse, urllib.request

GRAPH = 'https://graph.facebook.com/v21.0'
PAGES = [('mirsad', '1475210439010063', 'مرصد'), ('btw', '111570231877045', 'By the Way')]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'fb_pages.json')
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


def main():
    token = os.environ.get('FB_TOKEN', '').strip()
    if not token:
        raise SystemExit('FB_TOKEN is not set')

    acc = get('me/accounts', {'fields': 'id,name,access_token', 'limit': '100', 'access_token': token})
    by_id = {p['id']: p for p in acc.get('data', [])}

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
            posts.append({
                'id': p['id'],
                't': msg.split('\n')[0].strip()[:120],
                'b': msg,
                'img': p.get('full_picture', ''),
                'at': at,
                'url': p.get('permalink_url', ''),
            })
        pages[slug] = {'id': pid, 'name': name, 'posts': posts}
        print(f'{slug}: {len(posts)} posts')

    data = {'version': 1, 'updated': int(time.time() * 1000), 'pages': pages}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = ''
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            old = f.read()
    new = json.dumps(data, ensure_ascii=False, indent=1)
    # مقارنة بدون وقت التحديث، عشان منعملش كوميت كل نص ساعة من غير تغيير
    if old:
        try:
            o = json.loads(old)
            if json.dumps(o.get('pages'), ensure_ascii=False, sort_keys=True) == json.dumps(data['pages'], ensure_ascii=False, sort_keys=True):
                print('no change')
                return
        except Exception:
            pass
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(new + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
