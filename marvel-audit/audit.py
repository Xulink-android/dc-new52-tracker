import requests,bs4,re,csv,json,pathlib,time,unicodedata
from urllib.parse import urljoin
O=pathlib.Path("marvel-audit-results");O.mkdir(exist_ok=True)
base="https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/"
pages=["knights-until-avengers-disassembled/","guide-part-2-disassembled/","marvel-comics-from-avengers-disassembled-to-house-of-m/","guide-part-4-house-of-m/","guide-part-5-decimation/","marvel-comics-between-house-of-m-civil-war/","guide-part-7-civil-war/","marvel-comics-from-civil-war-to-secret-invasion/"]
urls=[("CBH",urljoin(base,p)) for p in pages]+[("CBRO",f"https://comicbookreadingorders.com/marvel/marvel-master-reading-order-part-{i}/") for i in range(5,10)]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; personal-reading-list-audit/2.0)"})
rows=[];errors=[];diagnostics=[];scope_violations=[];stop_found=False;unresolved=[]
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
   # Inspect all visible paragraphs and list items. CBH uses different page templates,
   # so a single "Issues:" selector misses most pages.
   sample=[]
   in_last_page=(url==urls[7][1])
   antman_heading_seen=False
   current_collection=""
   for node in main.select("li,p,h2,h3,h4"):
    if node.name=="p" and node.find_parent("li"):continue
    t=node.get_text(" ",strip=True)
    if not t or len(t)>1000:continue
    if in_last_page and not re.match(r"^(?:issues?|collects)\s*:",t,re.I):
     links=node.find_all("a")
     if links and len(t)<190:
      candidate=links[0].get_text(" ",strip=True)
      if candidate and not re.search(r"\b(?:amazon|kindle|comixology|buy now)\b",candidate,re.I):
       current_collection=candidate
    if in_last_page:
     # The first heading/title referring to Ant-Man marks the final collection.
     # Stop immediately after the next issues paragraph (which must contain #12).
     if re.search(r"irredeemable\s+ant[- ]man",t,re.I) and not re.search(r"\b(?:note|world war hulk)\b",t,re.I):
      antman_heading_seen=True
     if antman_heading_seen and re.search(r"\b(?:issues?|collects)\s*:",t,re.I) and re.search(r"#\s*12\b",t):
      stop_found=True
      print("ANTMAN STOP MARKER",t[:180],flush=True)
    if len(sample)<6 and ("#" in t or "Issues" in t):sample.append(t[:180])
    if in_last_page and re.match(r"^Issues?\s*:\s*#",t,re.I):
     ranges=re.findall(r"#(\d{1,4})(?:\s*(?:to|through|[-–])\s*#?(\d{1,4}))?",t,re.I)
     if current_collection and ranges:
      title=re.sub(r"\s*(?:vol(?:ume)?\.?\s*\d+|\(\d{4}\))\s*$","",current_collection,flags=re.I).strip()
      for lo,hi in ranges:
       start=int(lo);end=int(hi or lo)
       if start<=end and end-start<=120:
        for issue in range(start,end+1):add(src,title,issue,url,t)
     else:unresolved.append({"url":url,"text":t[:250],"collection":current_collection})
    for m in re.finditer(r"([A-Za-z][A-Za-z0-9&:''().,/ –-]{2,85}?)\s*#(\d{1,4})(?:\s*(?:to|through|[-–])\s*#?(\d{1,4}))?",t,re.I):
     title=m.group(1).strip(" :-–.,")
     first=int(m.group(2));last=int(m.group(3) or first)
     if last<first or last-first>120:continue
     for issue in range(first,last+1):add(src,title,issue,url,t)
    if in_last_page and stop_found:
     break
   print("CBH SAMPLES",url,json.dumps(sample,ensure_ascii=False),flush=True)
  if src=="CBH" and url==urls[7][1] and not stop_found:
   scope_violations.append("Irredeemable Ant-Man #12 stop not proven on final CBH page")
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
write("unresolved_issues.csv",unresolved,["url","text","collection"])
idx={}
for row in rows:idx.setdefault(row["source"],{}).setdefault((row["normalized"],row["issue"]),row)
a=idx.get("CBH",{});b=idx.get("CBRO",{})
write("cbh_non_correspondants.csv",[a[k] for k in sorted(a.keys()-b.keys())],fields)
write("cbro_non_correspondants.csv",[b[k] for k in sorted(b.keys()-a.keys())],fields)
write("communs.csv",[a[k] for k in sorted(a.keys()&b.keys())],fields)
report={"unresolved_issues":len(unresolved),"scope_violations":scope_violations,"antman_stop_found":stop_found,"warning":"DIAGNOSTIC UNIQUEMENT. Volumes ignorés dans les rapprochements; recueils et événements non exhaustifs. Aucun JSON modifié.","pages":len(urls),"errors":errors,"diagnostics":diagnostics,"cbh_unique":len(a),"cbro_unique":len(b),"common_approximate":len(a.keys()&b.keys()),"cbh_only_approximate":len(a.keys()-b.keys()),"cbro_only_approximate":len(b.keys()-a.keys())}
(O/"bilan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2),flush=True)
if errors or scope_violations:raise SystemExit(2)
