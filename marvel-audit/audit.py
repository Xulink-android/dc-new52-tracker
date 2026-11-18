import requests,bs4,re,csv,json,pathlib,time,unicodedata
from urllib.parse import urljoin
O=pathlib.Path("marvel-audit-results");O.mkdir(exist_ok=True)
base="https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/"
pages=["knights-until-avengers-disassembled/","guide-part-2-disassembled/","marvel-comics-from-avengers-disassembled-to-house-of-m/","guide-part-4-house-of-m/","guide-part-5-decimation/","marvel-comics-between-house-of-m-civil-war/","guide-part-7-civil-war/","marvel-comics-from-civil-war-to-secret-invasion/"]
urls=[("CBH",urljoin(base,p)) for p in pages]+[("CBRO",f"https://comicbookreadingorders.com/marvel/marvel-master-reading-order-part-{i}/") for i in range(5,10)]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; personal-reading-list-audit/2.0)"})
rows=[];errors=[];diagnostics=[]
def clean(t):
 t=unicodedata.normalize("NFKD",t).encode("ascii","ignore").decode().lower()
 t=re.sub(r"\b(?:the|marvel's)\b","",t)
 t=re.sub(r"\b(?:vol(?:ume)?\.?\s*\d+)\b","",t)
 return re.sub(r"[^a-z0-9]+","-",t).strip("-")
def add(src,title,issue,url,evidence,volume=""):
 title=re.sub(r"\s+"," ",title).strip(" :-–.,")
 if not title or len(title)>105:return
 rows.append(dict(source=src,title=title,normalized=clean(title),volume=volume,issue=str(issue),url=url,evidence=evidence[:250]))
issue_pattern=re.compile(r"(?:(?P<title>[A-Za-z][A-Za-z0-9 :&'().,/–-]{2,80}?)\s*)?#(?P<first>\d{1,4})(?:\s*(?:to|through|[-–])\s*#?(?P<last>\d{1,4}))?",re.I)
for src,url in urls:
 try:
  r=s.get(url,timeout=50);r.raise_for_status()
  soup=bs4.BeautifulSoup(r.text,"html.parser")
  main=soup.select_one("article .entry-content, .entry-content, article, main") or soup
  n0=len(rows)
  if src=="CBRO":
   # Only actual checkbox labels, not notes, links, or duplicate explanatory text.
   for label in main.select("label"):
    text=label.get_text(" ",strip=True)
    m=re.search(r"(?:Mark\s+)?(.+?)\s+#(\d{1,4})(?:\s+as read)?$",text,re.I)
    if m:add(src,m.group(1),m.group(2),url,text)
   # Some themes do not use labels: recover explicit 'Mark X #N as read' text.
   if len(rows)==n0:
    for node in main.find_all(string=re.compile(r"Mark .+?#\d+ as read",re.I)):
     t=str(node).strip();m=re.search(r"Mark (.+?) #(\d{1,4}) as read",t,re.I)
     if m:add(src,m.group(1),m.group(2),url,t)
  else:
   # CBH structure: a linked book title followed by 'Issues: ...'.
   # Keep the immediately preceding title, but prefer explicit titles in Issues.
   current=""
   for node in main.find_all(["p","h2","h3","h4","li"]):
    if node.find_parent(["li","p"]) and node.name not in ("li",):continue
    text=node.get_text(" ",strip=True)
    if not text or len(text)>900:continue
    if url==urls[7][1] and re.search(r"Irredeemable Ant-Man",text,re.I) and not text.lower().startswith("issues:"):
     # Stop after its following Issues line, not at title.
     stopping=True
    if re.match(r"^Issues?\s*:",text,re.I):
     body=re.sub(r"^Issues?\s*:\s*","",text,flags=re.I)
     for m in issue_pattern.finditer(body):
      title=(m.group("title") or current).strip(" :-–.,")
      a=int(m.group("first"));b=int(m.group("last") or a)
      if b<a or b-a>120:continue
      for i in range(a,b+1):add(src,title,i,url,text)
     if url==urls[7][1] and current.lower().startswith("irredeemable ant-man"):break
    else:
     # CBH collection titles generally appear as a single linked heading in a paragraph.
     links=node.find_all("a")
     if links and len(text)<160 and not re.match(r"^(note|previously|next|read|issues)\b",text,re.I):
      candidate=links[0].get_text(" ",strip=True)
      if len(candidate)>2 and not candidate.lower().startswith(("image","buy","amazon")):current=candidate
  diagnostics.append({"source":src,"url":url,"http":r.status_code,"extracted":len(rows)-n0})
  print(src,url,"extracted",len(rows)-n0,flush=True)
 except Exception as e:
  errors.append({"source":src,"url":url,"error":str(e)});print("ERROR",url,e,flush=True)
 time.sleep(.5)
def write(name,data,fields):
 with (O/name).open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
fields=["source","title","normalized","volume","issue","url","evidence"]
write("extractions.csv",rows,fields)
idx={}
for row in rows:idx.setdefault(row["source"],{}).setdefault((row["normalized"],row["issue"]),row)
a=idx.get("CBH",{});b=idx.get("CBRO",{})
write("cbh_non_correspondants.csv",[a[k] for k in sorted(a.keys()-b.keys())],fields)
write("cbro_non_correspondants.csv",[b[k] for k in sorted(b.keys()-a.keys())],fields)
write("communs.csv",[a[k] for k in sorted(a.keys()&b.keys())],fields)
report={"warning":"DIAGNOSTIC UNIQUEMENT. Volumes ignorés dans les rapprochements; recueils et événements non exhaustifs. Aucun JSON modifié.","pages":len(urls),"errors":errors,"diagnostics":diagnostics,"cbh_unique":len(a),"cbro_unique":len(b),"common_approximate":len(a.keys()&b.keys()),"cbh_only_approximate":len(a.keys()-b.keys()),"cbro_only_approximate":len(b.keys()-a.keys())}
(O/"bilan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2),flush=True)
if errors:raise SystemExit(2)
