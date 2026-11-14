"""jlcsearch.py KEYWORD...: JLC assembly-library search (code, model, brand, package, stock, library, price near 500 pcs)."""
import json, sys, urllib.request
def search(kw, n=25):
    body = json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n, "searchSource": "search"}).encode()
    req = urllib.request.Request('https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList', data=body,
                                 headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=25))
    out = []
    for c in (r.get('data') or {}).get('componentPageInfo', {}).get('list') or []:
        if str(c.get('componentCode', '')).startswith('C99'): continue        # customer-supplied placeholders
        p500 = None
        for p in c.get('componentPrices') or []:
            if p.get('startNumber', 0) <= 500: p500 = p.get('productPrice')
        out.append((c.get('stockCount') or 0, c.get('componentCode'), c.get('componentModelEn'), c.get('componentBrandEn'), c.get('componentSpecificationEn'), c.get('componentLibraryType'), p500))
    return sorted(out, reverse=True)
for kw in sys.argv[1:]:
    print('==', kw)
    try:
        for o in search(kw)[:8]: print('  ', o)
    except Exception as e: print('   ERR', str(e)[:100])
