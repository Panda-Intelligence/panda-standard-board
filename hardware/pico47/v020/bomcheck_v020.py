"""JLC stock and price check of every BOM line in netlist_v020.json (plain Python, JLC public parts API).

usage: bomcheck_v020.py netlist_v020.json
"""
import json, sys, urllib.request, collections, time
d = json.load(open(sys.argv[1]))
groups = collections.defaultdict(list)
for ref, p in d['parts'].items():
    if ref.startswith('TP') or p['dnp']: continue
    groups[(p['fields'].get('LCSC', ''), p['fields'].get('MPN', ''))].append(ref)
cache = {}
def detail(c):
    if c in cache: return cache[c]
    for _ in range(3):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request('https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode=' + c, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))['data']
            cache[c] = r; return r
        except Exception as e:
            time.sleep(1)
    return None
def price(dd, qty):
    best = None
    for p in dd.get('prices') or []:
        if qty >= p['startNumber']: best = p['productPrice']
    return best if best is not None else (dd['prices'][0]['productPrice'] if dd.get('prices') else None)
tot = {100: 0, 1000: 0}; rows = []; ext = 0
for (lcsc, mpn), refs in sorted(groups.items(), key=lambda x: x[1][0]):
    dd = detail(lcsc) if lcsc else None
    if not dd:
        rows.append(('MISSING', lcsc, mpn, refs)); continue
    n = len(refs)
    lib = dd.get('componentLibraryType'); ext += lib != 'base'
    p100, p1k = price(dd, 100 * n), price(dd, 1000 * n)
    tot[100] += (p100 or 0) * n; tot[1000] += (p1k or 0) * n
    rows.append((dd.get('stockCount'), lcsc, dd.get('componentModelEn'), lib, n, p100, ' '.join(refs)))
for r in rows:
    flag = '' if isinstance(r[0], int) and r[0] >= 50 else '  <-- STOCK'
    print(*r, flag)
print('lines', len(groups), 'extended', ext, 'placements', sum(len(v) for v in groups.values()))
print('parts $/board @100 %.2f  @1000 %.2f' % (tot[100], tot[1000]))
