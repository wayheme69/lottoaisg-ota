#!/usr/bin/env python3
"""Robot LOTTO AI SG : résultats officiels du 6/49 de Singapour (pages publiques de Singapore Pools).
- 30 derniers tirages (6 numéros, Additional Number, montant par part et nombre de parts gagnantes des 7 groupes)
- prochain tirage annoncé (date) + estimation du Group 1
Écrit sg_results.json UNIQUEMENT si tout est cohérent (sinon : sortie en erreur, l'ancien fichier reste).
Mode --history : exporte tous les tirages depuis le passage au 6/49 (tirage 2995, 09/10/2014) dans history.json."""
import json, urllib.request, base64, re, sys, datetime, time
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
B = "https://www.singaporepools.com.sg"
O = B + "/DataFileArchive/Lottery/Output/"
SGT = datetime.timezone(datetime.timedelta(hours=8))
FIRST = 2995

def fetch(url, tries=4):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "ignore")
        except Exception:
            if t == tries - 1: raise
            time.sleep(5 * (t + 1))

def day(s):  # « Thu, 08 Oct 2026 »
    return datetime.datetime.strptime(s.strip(), "%a, %d %b %Y").date().isoformat()

def money(s):
    s = s.strip()
    return None if s in ("-", "") else float(s.replace("$", "").replace(",", ""))

def parse(block):
    """Un tirage (bloc HTML « tables-wrap »)"""
    no = int(re.search(r"class='drawNumber'>\s*Draw No\.\s*(\d+)", block).group(1))
    date = day(re.search(r"class='drawDate'>([^<]+)", block).group(1))
    nums = [int(re.search(rf"class='win{i}'>\s*(\d+)", block).group(1)) for i in range(1, 7)]
    add = int(re.search(r"class='additional'>\s*(\d+)", block).group(1))
    assert len(set(nums + [add])) == 7 and all(1 <= n <= 49 for n in nums + [add]), no
    m = re.search(r"class='jackpotPrize'>\s*([^<]+)", block)
    pay, win = {}, {}
    for g, amt, sh in re.findall(r"<td[^>]*>\s*Group\s*(\d)\s*</td>\s*<td[^>]*>\s*([^<]*)</td>\s*<td[^>]*>\s*([^<]*)</td>", block):
        a, n = money(amt), money(sh)
        pay[g] = a if n else None
        win[g] = int(n) if n and float(n).is_integer() else (n or 0)
    return {"draw": no, "date": date, "numbers": sorted(nums), "bonus": [add],
            "group1Prize": money(m.group(1)) if m else None, "payouts": pay or None, "winners": win or None}

def blocks(html):
    parts = html.split("<div class='tables-wrap'>")[1:]
    return [parse(p) for p in parts if "class='drawNumber'" in p]

def page(n):
    q = base64.b64encode(f"DrawNumber={n}".encode()).decode()
    b = blocks(fetch(f"{B}/en/product/sr/Pages/toto_results.aspx?sppl={q}"))
    assert b and b[0]["draw"] == n, f"page {n}"
    return b[0]

def specials():
    out = {}
    for kind in ("hongbao", "special"):
        for v in re.findall(r"value='(\d+)'", fetch(O + f"toto_result_{kind}_draw_list_en.html")):
            out[int(v)] = kind
    return out

def complete(d):
    # Tableau publié : les 7 groupes présents et les 3 groupes fixes (S$50 / 25 / 10) avec des gagnants
    w = d.get("winners") or {}
    return len(w) == 7 and all(w.get(g, 0) > 0 for g in ("5", "6", "7"))

if len(sys.argv) > 1 and sys.argv[1] == "--history":
    lst = re.findall(r"value='(\d+)'", fetch(O + "toto_result_draw_list_en.html"))
    last = int(lst[0]); rows = []
    for n in range(FIRST, last + 1):
        rows.append(page(n)); time.sleep(0.4)
    sp = specials()
    for r in rows:
        if r["draw"] in sp: r["special"] = sp[r["draw"]]
    assert [r["draw"] for r in rows] == list(range(FIRST, last + 1))
    assert all(a["date"] < b["date"] for a, b in zip(rows, rows[1:]))
    json.dump(rows, open("history.json", "w"), ensure_ascii=False)
    print("history", len(rows), rows[0]["draw"], rows[-1]["draw"], sum(not complete(r) for r in rows), "incomplets"); sys.exit(0)

lst = re.findall(r"value='(\d+)' winningSharesUploaded='(\w*)' isCancelled='(\w*)'", fetch(O + "toto_result_draw_list_en.html"))
want = [(int(v), up == "True") for v, up, c in lst if not c][:30]
try: old = {d["draw"]: d for d in json.load(open("sg_results.json"))["toto"]}
except (OSError, ValueError, KeyError): old = {}
top = {d["draw"]: d for d in blocks(fetch(O + "toto_result_top_draws_en.html"))}
try: sp = specials()
except Exception: sp = {d: o.get("special") for d, o in old.items() if o.get("special")}
res = []
for n, uploaded in want:
    if n in top: d = top[n]
    elif n in old and complete(old[n]): d = old[n]
    else: d = page(n); time.sleep(0.3)
    if not uploaded or not complete(d):  # numéros publiés, parts pas encore : lots inconnus
        d = {**d, "payouts": None, "winners": None}
    if n in sp: d["special"] = sp[n]
    res.append(d)
res.sort(key=lambda r: r["draw"], reverse=True)
assert len(res) >= 25, f"seulement {len(res)} tirages"
assert [r["draw"] for r in res] == list(range(res[0]["draw"], res[0]["draw"] - len(res), -1)), "numéros non consécutifs"
nxt = {}
try:
    h = fetch(O + "toto_next_draw_estimate_en.html")
    m = re.search(r"toto-draw-date'>\s*([A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4})", h)
    if m: nxt["date"] = day(m.group(1))
    j = re.search(r"\$([\d,]+)\s*est", h)
    if j: nxt["estimatedPrize"] = int(j.group(1).replace(",", ""))
except Exception as e:
    print("prochain tirage indisponible :", e)
try:
    o = json.load(open("sg_results.json"))
    if o.get("toto") == res and o.get("next") == nxt:
        print("inchangé", res[0]["draw"]); sys.exit(0)
except (OSError, ValueError):
    pass
json.dump({"toto": res, "next": nxt, "updated": datetime.datetime.now(SGT).isoformat(timespec="minutes")},
          open("sg_results.json", "w"), ensure_ascii=False, indent=1)
print("ok", len(res), res[0]["draw"], res[0]["date"], nxt)
