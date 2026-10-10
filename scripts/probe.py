import urllib.request, base64, json, os
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
B = "https://www.singaporepools.com.sg"
O = B + "/DataFileArchive/Lottery/Output/"
urls = {
 "draw_list": O + "toto_result_draw_list_en.html",
 "top_draws": O + "toto_result_top_draws_en.html",
 "next": O + "toto_next_draw_estimate_en.html",
 "cascade": O + "toto_result_cascade_draw_list_en.html",
 "hongbao": O + "toto_result_hongbao_draw_list_en.html",
 "special": O + "toto_result_special_draw_list_en.html",
 "page_4224": B + "/en/product/sr/Pages/toto_results.aspx?sppl=" + base64.b64encode(b"DrawNumber=4224").decode(),
 "page_2999": B + "/en/product/sr/Pages/toto_results.aspx?sppl=" + base64.b64encode(b"DrawNumber=2999").decode(),
}
os.makedirs("probe", exist_ok=True); out = {}
for k, u in urls.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60)
        b = r.read(); out[k] = {"status": r.status, "len": len(b)}
        open(f"probe/{k}.html", "wb").write(b)
    except Exception as e: out[k] = {"error": repr(e)}
json.dump(out, open("probe/summary.json", "w"), indent=1); print(out)
