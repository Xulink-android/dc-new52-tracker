#!/usr/bin/env python3
"""Import factual issue titles and link positions from three public CBRO New 52 pages.
Uses only bibliographic labels and links; no article commentary or full prose.
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

PAGES=[
("1","New 52 — Partie 1","https://comicbookreadingorders.com/dc/new-52-reading-order-part-1/",640),
("2","New 52 — Partie 2","https://comicbookreadingorders.com/dc/new-52-reading-order-part-2/",605),
("3","New 52 — Partie 3","https://comicbookreadingorders.com/dc/new-52-reading-order-part-3/",698),
]
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"issue-tracker"/"catalog.json"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; personal-reading-tracker/1.0; +https://github.com/Xulink-android/dc-new52-tracker)","Accept-Language":"en-US,en;q=0.9"}
PAT=re.compile(r"Mark\s+(.+?)\s+as read\s*$",re.I)
MAX_ITEMS=1500
def extract(page_id, label, url, expected):
  r=requests.get(url,timeout=40,headers=HEADERS);r.raise_for_status()
  soup=BeautifulSoup(r.text,"html.parser")
  candidates=[]
  for el in soup.find_all(True):
    for val in (el.get("aria-label"),el.get("title"),el.get("data-label")):
      if not isinstance(val,str):continue
      match=PAT.search(val.strip())
      if match:
        candidates.append((el,match.group(1).strip()))
        break
  if len(candidates)<expected:
    # Fallback for text nested in labels rather than checkbox aria-label.
    for el in soup.find_all(["label","button"]):
      text=el.get_text(" ",strip=True)
      match=PAT.search(text)
      if match and all(el is not x for x,_ in candidates):
        candidates.append((el,match.group(1).strip()))
  output=[]
  seen_nodes=set()
  for el,title in candidates:
    if id(el) in seen_nodes:continue
    seen_nodes.add(id(el))
    # Prefer row ancestor, which usually contains event links and status descriptors.
    row=el.find_parent("li")
    if row is None:
      row=el.find_parent(["article","section"])
    if row is None:row=el.parent
    desc=row.get_text(" ",strip=True)[:600] if row else ""
    is_event=bool(re.search(r"\bEvent\b",desc)) and not bool(re.search(r"#\d",title))
    if " # " in title: title=re.sub(r"\s+"," ",title)
    src=""
    if row:
      links=[a.get("href") for a in row.find_all("a",href=True)]
      links=[urljoin(url,x) for x in links if x]
      internal=[x for x in links if urlparse(x).netloc.endswith("comicbookreadingorders.com") and "/events/" in x]
      src=(internal or [url])[0]
    if not src:src=url
    if not is_event and not re.search(r"#\d+(?:\.\d+)?(?:\b|$)",title):
      # A named crossover with a link can still be an event.
      is_event=("Event" in desc or "/events/" in src)
    output.append({
      "id":f"cbr-{page_id}-{len(output)+1:04d}",
      "order":len(output)+1,
      "title":title,
      "kind":"event" if is_event else "issue",
      "url":src,
    })
  issue_count=sum(x["kind"]=="issue" for x in output)
  events=sum(x["kind"]=="event" for x in output)
  print(f"Part {page_id}: HTTP {r.status_code}; raw HTML {len(r.content)} bytes; {len(candidates)} candidate controls; {issue_count} issues, {events} events",flush=True)
  if issue_count < expected - 20 or issue_count>expected + 35:
    print("FIRST CONTROLS:",[(x["title"],x["kind"]) for x in output[:12]],flush=True)
    print("HTML SAMPLE:",str(soup.find(string=re.compile("Mark Dial H")) or "")[:400],flush=True)
    raise ValueError(f"Part {page_id}: expected around {expected} single issues, got {issue_count}. Refusing to publish partial data.")
  if len(output)>MAX_ITEMS:raise ValueError("Unexpected page size")
  return {"id":page_id,"name":label,"url":url,"expectedIssues":expected,"issues":issue_count,"events":events,"items":output}
def extract_event(parent):
  """Extract issue names from the source event's ordered list, leaving note rows untouched."""
  url=parent["url"]
  r=requests.get(url,timeout=45,headers=HEADERS)
  r.raise_for_status()
  soup=BeautifulSoup(r.text,"html.parser")
  found=[]
  for row in soup.select("ol.issues li.issue"):
    node=row.select_one(".issue-title")
    title=node.get_text(" ",strip=True) if node else ""
    if not title:
      label=row.select_one("label.check .sr")
      match=PAT.search(label.get_text(" ",strip=True)) if label else None
      title=match.group(1).strip() if match else ""
    if title:
      found.append({
        "id":f'{parent["id"]}-issue-{len(found)+1:03d}',
        "order":len(found)+1,
        "title":title,
      })
  if len(found)<1 or len(found)>500:
    raise ValueError(f"Unexpected event list length {len(found)} for {url}")
  print(f"Event {parent['title']}: {len(found)} issues",flush=True)
  return found

def main():
  parts=[]
  for x in PAGES:
    parts.append(extract(*x))
    time.sleep(.8)
  n=sum(p["issues"] for p in parts)
  if n<1900:raise ValueError("Incomplete reading order")
  event_count=0
  event_issue_total=0
  failed=[]
  for p in parts:
    for parent in p["items"]:
      if parent["kind"]!="event":continue
      if parent["title"]=="DC You":
        parent["separatePeriod"]=True
        continue
      try:
        parent["subIssues"]=extract_event(parent)
        event_count+=1
        event_issue_total+=len(parent["subIssues"])
      except Exception as exc:
        parent["eventImportError"]=str(exc)
        failed.append((parent["title"],str(exc)))
        print("EVENT IMPORT ERROR",parent["title"],str(exc),flush=True)
      time.sleep(.4)
  if event_count<20:
    raise ValueError(f"Only {event_count} event lists imported; refusing incomplete release. {failed}")
  output={
    "eventIssuesTotal":event_issue_total,
    "eventListsImported":event_count,
    "eventListsFailed":failed,
    "source":"Comic Book Reading Orders",
    "sourceUrl":PAGES[0][2],
    "scope":"Three New 52 parts, events referenced in place. DC You is separate.",
    "version":1,
    "parts":parts,
    "issuesTotal":n,
    "eventsTotal":sum(p["events"] for p in parts),
  }
  OUT.parent.mkdir(parents=True,exist_ok=True)
  OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
  print("Saved",OUT,"bytes",OUT.stat().st_size,flush=True)
if __name__=="__main__":main()
