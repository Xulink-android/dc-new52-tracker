import requests,bs4,re,csv,json,pathlib,time
from urllib.parse import urljoin
O=pathlib.Path("marvel-audit-results");O.mkdir(exist_ok=True)
base="https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/"
pages=["knights-until-avengers-disassembled/","guide-part-2-disassembled/","marvel-comics-from-avengers-disassembled-to-house-of-m/","guide-part-4-house-of-m/","guide-part-5-decimation/","marvel-comics-between-house-of-m-civil-war/","guide-part-7-civil-war/","marvel-comics-from-civil-war-to-secret-invasion/"]
urls=[("CBH",urljoin(base,p)) for p in pages]+[("CBRO",f"https://comicbookreadingorders.com/marvel/marvel-master-reading-order-part-{i}/") for i in range(5,10)]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; personal-reading-list-audit/1.0)"})
rows=[];errors=[]
for src,url in urls:
 try:
  r=s.get(url,timeout=50);r.raise_for_status()
  soup=bs4.BeautifulSoup(r.text,"html.parser")
  main=soup.select_one("article .entry-content, .entry-content, article, main") or soup
  tags=main.select("li,p,h2,h3,h4")
  n=0
  for tag in tags:
   if tag.name=="p" and tag.find_parent("li"):continue
   t=tag.get_text(" ",strip=True)
   if not t or len(t)>700:continue
   for m in re.finditer(r"([A-Za-z][A-Za-z0-9&:'()., /-]{2,80}?)\s*#(\d{1,4})(?:\s*[-–]\s*#?(\d{1,4}))?",t):
    title=re.sub(r"[^a-z0-9]+","-",m.group(1).lower()).strip("-")
    a=int(m.group(2));b=int(m.group(3) or a)
    if b<a or b-a>150:continue
    for issue in range(a,b+1):
     rows.append(dict(source=src,title=title,issue=issue,url=url,evidence=t[:350]));n+=1
  print(src,url,r.status_code,"extracted",n,flush=True)
 except Exception as e:
  errors.append(dict(source=src,url=url,error=str(e)));print("ERROR",url,e,flush=True)
 time.sleep(1)
def write(name,data,fields):
 with (O/name).open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
fields=["source","title","issue","url","evidence"]
write("extractions.csv",rows,fields)
idx={}
for row in rows:idx.setdefault(row["source"],{}).setdefault((row["title"],row["issue"]),row)
a=idx.get("CBH",{});b=idx.get("CBRO",{})
write("cbh_non_correspondants.csv",[a[k] for k in sorted(a.keys()-b.keys())],fields)
write("cbro_non_correspondants.csv",[b[k] for k in sorted(b.keys()-a.keys())],fields)
write("communs.csv",[a[k] for k in sorted(a.keys()&b.keys())],fields)
report={"warning":"PRE-AUDIT HEURISTIQUE, NON EXHAUSTIF. Titres de recueils, volumes, pages hors périmètre et limite Ant-Man non encore résolus. Aucun JSON de progression modifié.","pages":len(urls),"errors":errors,"cbh_unique":len(a),"cbro_unique":len(b),"common_exact":len(a.keys()&b.keys()),"cbh_only_exact":len(a.keys()-b.keys()),"cbro_only_exact":len(b.keys()-a.keys())}
(O/"bilan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2),flush=True)
if errors:raise SystemExit(2)
