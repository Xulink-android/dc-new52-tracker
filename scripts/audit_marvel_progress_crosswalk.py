#!/usr/bin/env python3
"""Public bibliographic crosswalk: titles/issues in five CBH guides vs CBRO Marvel master and its event pages. No account data."""
import json,re,sys,unicodedata,zlib,base64,time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
S=requests.Session();S.headers.update({"User-Agent":"Mozilla/5.0 (compatible; bibliographic-reading-list-audit/1.0)","Accept-Language":"en-US,en;q=.9"})
B="https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/"
CBRO="https://comicbookreadingorders.com/marvel/"
GUIDES={
 "pre":B+"marvel-comics-from-avengers-disassembled-to-house-of-m/",
 "house":B+"guide-part-4-house-of-m/",
 "decim":B+"guide-part-5-decimation/",
 "civil":B+"guide-part-7-civil-war/",
 "after":B+"marvel-comics-from-civil-war-to-secret-invasion/"
}
def get(u):
 r=S.get(u,timeout=40);r.raise_for_status()
 print("FETCH",r.status_code,len(r.content),u,flush=True)
 return BeautifulSoup(r.content,"html.parser")
def norm(s):
 s=unicodedata.normalize("NFKD",s.lower()).encode("ascii","ignore").decode()
 s=s.replace("uncannly","uncanny").replace("frontline","front line").replace("solider","soldier")
 s=re.sub(r"\bvol(?:ume)?\.?\s*\d+\b"," ",s)
 s=re.sub(r"\((?:19|20)\d\d\)"," ",s)
 s=re.sub(r"\b(the|marvel|comics|limited series)\b"," ",s)
 s=re.sub(r"[^a-z0-9]+"," ",s).strip()
 alias={"uncanny":"uncanny x men","new x men academy x":"new x men","incredible hulk":"incredible hulk","the incredible hulk":"incredible hulk",
   "iron man director of shield":"iron man","iron man director of s h i e l d":"iron man",
   "sensational spider man":"sensational spider man","dark avengers thunderbolts":"thunderbolts",
   "sentinel squad":"sentinel squad o n e","decimation sentinel squad o n e":"sentinel squad o n e",
   "decimation x men generation m":"generation m","decimation x men son of m":"son of m",
   "black panther":"black panther","house of m incredible hulk":"incredible hulk","new thunderbolts":"new thunderbolts",
   "hulk":"incredible hulk", "x men deadly genesis":"x men deadly genesis",
   "x men 198":"x men 198","decimation x men day after":"decimation house of m day after",
   "spider man breakout":"spider man breakout","civil war fallen son death of captain america":"fallen son death of captain america",
   "civil war fallen son":"fallen son death of captain america",
   "irredeemable ant man":"irredeemable ant man"}
 return alias.get(s,s)
def source_key(raw):
 m=re.search(r"(.+?)\s*#\s*(\d+)\b",raw)
 if not m:return None
 return norm(m.group(1)),int(m.group(2))
def add(read,raw,guide):
 raw=re.sub(r"\s+"," ",raw.replace("\xa0"," ")).strip()
 raw=re.sub(r"^[\u2022\-\*]+\s*","",raw)
 raw=re.sub(r"\s*\((?:19|20)\d\d[^)]*\)","",raw)
 # Some source entry lines append notes; capture first series + its first explicit issue and numerical range.
 pat=re.search(r"(.*?)\s*#\s*(\d+)\s*(?:(?:to|[-–—])\s*#?\s*(\d+))?",raw,flags=re.I)
 if not pat:return 0
 series=pat.group(1).strip(" :,;-")
 if series.lower().startswith("issues:"):return 0
 if series.lower().startswith("decimation: house of m: the day after"):series="Decimation: House of M: The Day After"
 a=int(pat.group(2));b=int(pat.group(3) or a)
 if b<a or b-a>100:return 0
 for n in range(a,b+1):read.setdefault((norm(series),n),set()).add(guide)
 return b-a+1
def entries_within(soup,start,stop=None):
 root=soup.select_one(".entry-content") or soup.select_one("article") or soup
 active=False;rows=[]
 for item in root.find_all(["h2","h3","h4","li","p"]):
  if item.find_parent(["li","p"]) is not None:continue
  t=item.get_text(" ",strip=True)
  if re.search(start,t,re.I) and item.name.startswith("h"):
   active=True;continue
  if active and stop and re.search(stop,t,re.I):break
  if active and item.name in ["li","p"] and t:rows.append(t)
 return rows
def extract_cbh():
 req={}
 pages={k:get(u) for k,u in GUIDES.items()}
 sections={
  "pre":entries_within(pages["pre"],r"Getting From Avengers Disassembled",r"^Next:|Heroically Support|### Comments"),
  "house":entries_within(pages["house"],r"Official Marvel Digital",r"^Next:|Heroically Support"),
  "decim":entries_within(pages["decim"],r"Issue by Issue Decimation",r"^Next:|Heroically Support"),
  "civil":entries_within(pages["civil"],r"Marvel Unlimited Event Reading",r"^Next:|Heroically Support"),
 }
 for k,rows in sections.items():
  print("CBH_ROWS",k,len(rows),"HEAD",json.dumps(rows[:9],ensure_ascii=False),"TAIL",json.dumps(rows[-5:],ensure_ascii=False),flush=True)
  for raw in rows:add(req,raw,k)
 # Add the Decimation trade-only issue ranges explicitly, since CBH's digital list omits them.
 for raw in ["Uncanny X-Men #466-474","New Excalibur #1-5","X-Men #177-181","X-Factor #1-6"]:
  add(req,raw,"decim-trades")
 # Add House of M trade-only prequels explicitly listed in CBH.
 for raw in ["House of M: Civil War #1-5","House of M: Masters of Evil #1-4","House of M: Avengers #1-5"]:
  add(req,raw,"house-trades")
 # Interpret 'up to and including all twelve Irredeemable Ant-Man issues' as all entries above Ant-Man in CBH.
 after=[
 "Incredible Hulk #92-95","Giant-Size Hulk #1","Incredible Hulk #96-105",
 "Iron Man #15-32","Fallen Son: The Death of Captain America #1-5",
 "Captain America #26-45","Mighty Avengers #1-11","Avengers: The Initiative #1-13",
 "The Order #1-10","Amazing Spider-Man #539-545","Friendly Neighborhood Spider-Man #17-24",
 "Sensational Spider-Man #35-41","New Avengers #26-37","New Avengers Annual #2",
 "Thunderbolts #110-121","Punisher War Journal #4-23","Irredeemable Ant-Man #1-12",
 ]
 for raw in after:add(req,raw,"after-through-antman")
 print("CBH_TOTAL_EXPLICIT_KEYS",len(req),"BY_GUIDE",json.dumps({g:sum(g in v for v in req.values()) for g in ["pre","house","decim","civil","decim-trades","house-trades","after-through-antman"]}),flush=True)
 return req
def collect(soup,url):
 out=[];events=[]
 for row in soup.select("ol.issues li.issue"):
  t=row.select_one(".issue-title")
  title=t.get_text(" ",strip=True) if t else ""
  inp=row.select_one("label.check input[data-id]")
  if title and inp:
   k=source_key(title)
   out.append({"title":title,"key":k,"id":inp.get("data-id"),"url":url})
  elif row.select_one("a[href*='/events/']"):
   a=row.select_one("a[href*='/events/']")
   link=urljoin(url,a["href"])
   if link not in events:events.append(link)
 return out,events
def main():
 req=extract_cbh()
 records=[];evs=[]
 for n in [6,7,8]:
  u=CBRO+f"marvel-master-reading-order-part-{n}/"
  a,b=collect(get(u),u);records+=a;evs+=b
  print("MASTER",n,len(a),len(b),flush=True)
  time.sleep(.5)
 evs=list(dict.fromkeys(evs))
 print("EVENT_URLS",json.dumps(evs,ensure_ascii=False),flush=True)
 for u in evs:
  try:
   a,_=collect(get(u),u);records+=a
   print("EVENT",u.split("/")[-2],len(a),flush=True)
  except Exception as exc:print("EVENT_ERROR",str(exc),u,flush=True)
  time.sleep(.15)
 grouped={}
 for item in records:
  if item["key"]:grouped.setdefault(item["key"],[]).append(item)
 matched={};amb=[];missing=[]
 for k,provenance in req.items():
  poss=grouped.get(k,[])
  ids={p["id"] for p in poss}
  if len(ids)==1:matched[k]=next(iter(ids))
  elif len(ids)>1:amb.append((k,[(p["title"],p["id"]) for p in poss[:5]]))
  else:missing.append(k)
 # Issues repeated in event pages/master may have the same ID.
 print("CHECK_RESULT",json.dumps({"recordCount":len(records),"cbhExplicit":len(req),"matched":len(matched),"ambiguous":len(amb),"missing":len(missing),"missingSamples":missing[:160],"ambiguousSamples":amb[:40]},ensure_ascii=False),flush=True)
 ids=sorted(set(matched.values()))
 payload={"readIds":ids,"meta":{"matched":len(matched),"unmatched":len(missing),"ambiguous":len(amb),"sourceIssueCount":len(req),"siteIssueCount":len(records)}}
 token=base64.b64encode(zlib.compress(json.dumps(payload,separators=(",",":")).encode(),9)).decode()
 print("PROGRESS_PAYLOAD_ZLIB_BASE64",token,flush=True)
 print("PROGRESS_PAYLOAD_END",flush=True)
if __name__=="__main__":main()
