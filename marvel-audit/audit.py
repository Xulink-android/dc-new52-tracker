import requests,bs4,re,csv,json,pathlib,time,unicodedata
from urllib.parse import urljoin
O=pathlib.Path("marvel-audit-results");O.mkdir(exist_ok=True)
base="https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/"
pages=["knights-until-avengers-disassembled/","guide-part-2-disassembled/","marvel-comics-from-avengers-disassembled-to-house-of-m/","guide-part-4-house-of-m/","guide-part-5-decimation/","marvel-comics-between-house-of-m-civil-war/","guide-part-7-civil-war/","marvel-comics-from-civil-war-to-secret-invasion/"]
urls=[("CBH",urljoin(base,p)) for p in pages]+[("CBRO",f"https://comicbookreadingorders.com/marvel/marvel-master-reading-order-part-{i}/") for i in range(1,11)]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; personal-reading-list-audit/2.0)"})
rows=[];errors=[];diagnostics=[];scope_violations=[];stop_found=False;unresolved=[];suspect=[];ordering_notes=[]
def clean(t):
 t=unicodedata.normalize("NFKD",t).encode("ascii","ignore").decode().lower()
 t=re.sub(r"\b(?:the|marvel's)\b","",t)
 t=re.sub(r"\b(?:vol(?:ume)?\.?\s*\d+)\b","",t)
 return re.sub(r"[^a-z0-9]+","-",t).strip("-")
def add(src,title,issue,url,evidence,volume=""):
 title=re.sub(r"\s+"," ",title).strip(" :-–.,")
 series_year_match=re.search(r"\((19\d{2}|20\d{2})\)\s*$",title)
 series_start_year=series_year_match.group(1) if src=="CBH" and series_year_match else ""
 title=re.sub(r"^(?:collects?|issues?)\s*:\s*","",title,flags=re.I).strip()
 title=re.sub(r"\s*\(\s*$","",title).strip()
 title=re.sub(r"\s*\(\d{4}\)\s*$","",title).strip()
 if not title or len(title)>105:return
 cbh_group_date=""
 if src=="CBH" and len(re.findall(r"#\\s*\\d+",evidence))<=2:
  # Avoid attaching a date from one comic to another in multi-series commentary.
  date_match=re.search(r"\((?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+)?[\u2019\u0027]?(\d{2}|(?:19|20)\d{2})\)",evidence,re.I)
  if date_match:
   year=date_match.group(2)
   cbh_group_date=(date_match.group(1)+" " if date_match.group(1) else "")+(("20" if int(year)<50 else "19")+year if len(year)==2 else year)
 rows.append(dict(source=src,title=title,normalized=clean(title),volume=volume,issue=str(issue),url=url,evidence=evidence[:250],series_start_year=series_start_year,cbh_group_date=cbh_group_date))
issue_pattern=re.compile(r"(?:(?P<title>[A-Za-z][A-Za-z0-9 :&'().,/–-]{2,80}?)\s*)?#(?P<first>\d{1,4})(?:\s*(?:to|through|[-–])\s*#?(?P<last>\d{1,4}))?",re.I)
for src,url in urls:
 try:
  r=s.get(url,timeout=50);r.raise_for_status()
  soup=bs4.BeautifulSoup(r.text,"html.parser")
  main=soup.select_one("article .entry-content, .entry-content, article, main") or soup
  n0=len(rows)
  if src=="CBRO":
   # Only actual checkbox labels, not notes, links, or duplicate explanatory text.
   debug_labels=0
   debug_issues=0
   for label in main.select("label"):
    if debug_labels<2:
     print("CBRO LABEL HTML",str(label.parent)[:1400],flush=True)
     debug_labels+=1
    text=label.get_text(" ",strip=True)
    m=re.search(r"(?:Mark\s+)?(.+?)\s+#(\d{1,4})(?:\s+as read)?$",text,re.I)
    if m:
     if debug_issues<3:
      print("CBRO ISSUE HTML",str(label.parent)[:2000],flush=True)
      debug_issues+=1
     add(src,m.group(1),m.group(2),url,text)
     # Preserve the exact checkbox locator for future JSON reconciliation.
     checkbox=label.find("input",attrs={"type":"checkbox"})
     if checkbox is None and label.get("for"):
      checkbox=main.find("input",id=label.get("for"))
     if checkbox is not None:
      rows[-1]["checkbox_id"]=checkbox.get("data-id","") or checkbox.get("id","")
      rows[-1]["checkbox_name"]=checkbox.get("name","")
      rows[-1]["checkbox_value"]=checkbox.get("value","")
     # CBRO prints issue publication year beside each checkbox.
     # Capture it as evidence; do not confuse this with reading-order era.
     # The publication year is commonly a sibling of the label, not inside it.
     # Inspect only the closest issue-specific parent and only if it contains
     # exactly one issue checkbox/label, avoiding cross-issue contamination.
     context=text
     parent=label.parent
     if parent is not None:
      sibling_labels=parent.select("label")
      if len(sibling_labels)==1:
       context=parent.get_text(" ",strip=True)
     year_match=re.search(r"\b(?:19|20)\d{2}\b",context)
     if year_match:
      rows[-1]["publication_year"]=year_match.group(0)
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
    if re.search(r"\\b(?:read|between|before|after|in between)\\b",t,re.I) and re.search(r"#\\s*\\d+",t) and re.search(r"\\b(?:between|before|after|in between)\\b",t,re.I):
     ordering_notes.append({"url":url,"instruction":t[:450],"review":"ORDER_CONSTRAINT_NOT_YET_APPLIED"})
    if len(sample)<6 and ("#" in t or "Issues" in t):sample.append(t[:180])
    if in_last_page and re.match(r"^Issues?\s*:\s*#",t,re.I):
     ranges=re.findall(r"#(\d{1,4})(?:\s*(?:to|through|[-–])\s*#?(\d{1,4}))?",t,re.I)
     if current_collection and ranges:
      title=re.sub(r"\s*(?:vol(?:ume)?\.?\s*\d+|\(\d{4}\))\s*$","",current_collection,flags=re.I).strip()
      if re.search(r"\b(?:read|guide|collection|trade|amazon|buy|complete|omnibus)\b",title,re.I):suspect.append({"url":url,"title":title,"evidence":t[:250],"reason":"possible collection/marketing title"})
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
  if src=="CBH" and url==urls[7][1] and stop_found:
   antman=[x for x in rows[n0:] if re.search(r"irredeemable[- ]ant[- ]man",x["title"],re.I)]
   antman_issues={int(x["issue"]) for x in antman}
   if not set(range(1,13)).issubset(antman_issues):
    scope_violations.append("Ant-Man #1-12 not all extracted: "+str(sorted(antman_issues)))
   if any(i>12 for i in antman_issues):
    scope_violations.append("Ant-Man issues beyond #12 extracted")
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
fields=["source","title","normalized","volume","issue","url","evidence","publication_year","checkbox_id","checkbox_name","checkbox_value","series_start_year","cbh_group_date"]
write("extractions.csv",rows,fields)

# Evidence audit: CBH ranges must carry dates only from their own textual entry.
# Do not treat a CBH group date as the series launch year.
cbh_dates=[x for x in rows if x["source"]=="CBH" and x.get("cbh_group_date")]
date_examples=[]
seen_date_examples=set()
for x in cbh_dates:
 key=(x["title"],x["cbh_group_date"],x["url"])
 if key not in seen_date_examples:
  seen_date_examples.add(key)
  date_examples.append({"title":x["title"],"issue":x["issue"],"cbh_group_date":x["cbh_group_date"],"evidence":x["evidence"],"url":x["url"]})
write("dates_groupes_cbh_exemples.csv",date_examples,["title","issue","cbh_group_date","evidence","url"])
print("CBH GROUP DATES",len(cbh_dates),"UNIQUE EXAMPLES",len(date_examples),flush=True)

write("unresolved_issues.csv",unresolved,["url","text","collection"])
write("suspect_contexts.csv",suspect,["url","title","evidence","reason"])
write("instructions_ordre_cbh.csv",ordering_notes,["url","instruction","review"])
idx={}
for row in rows:idx.setdefault(row["source"],{}).setdefault((row["normalized"],row["issue"]),row)
a=idx.get("CBH",{});b=idx.get("CBRO",{})
write("cbh_non_correspondants.csv",[a[k] for k in sorted(a.keys()-b.keys())],fields)
write("cbro_non_correspondants.csv",[b[k] for k in sorted(b.keys()-a.keys())],fields)
write("communs.csv",[a[k] for k in sorted(a.keys()&b.keys())],fields)

# Conservative matching: do not validate ambiguous volume identities or titles.
# Distinguish candidates from automatically safe matches.
from collections import defaultdict
titles_by_key=defaultdict(set)
for row in rows:
 titles_by_key[(row["source"],row["normalized"])].add(row["title"].lower().strip())
safe=[];review=[]
for k in sorted(a.keys()&b.keys()):
 left,right=a[k],b[k]
 same_title=left["title"].lower().strip()==right["title"].lower().strip()
 has_volume=bool(re.search(r"\b(?:vol(?:ume)?\.?\s*\d+|\(\d{4}\))\b",left["title"]+" "+right["title"],re.I))
 ambiguous=len(titles_by_key[("CBH",k[0])])>1 or len(titles_by_key[("CBRO",k[0])])>1
 rec={"title_cbh":left["title"],"title_cbro":right["title"],"issue":left["issue"],"cbh_url":left["url"],"cbro_url":right["url"],"reason":""}
 if same_title and not has_volume and not ambiguous:
  rec["reason"]="identical title and issue; volume not independently verified"
  safe.append(rec)
 else:
  rec["reason"]="volume or title identity requires verification"
  review.append(rec)
match_fields=["title_cbh","title_cbro","issue","cbh_url","cbro_url","reason"]
write("correspondances_titres_identiques.csv",safe,match_fields)
write("correspondances_a_verifier.csv",review,match_fields)

# Date audit uses distinct semantics, never a year-equality rule:
# CBH parenthetical year = series launch; CBRO year = individual issue.
chronology=[]
for k in sorted(a.keys()&b.keys()):
 left,right=a[k],b[k]
 sy=left.get("series_start_year","")
 iy=right.get("publication_year","")
 chronology.append({"title_cbh":left["title"],"title_cbro":right["title"],"issue":left["issue"],"cbh_series_start_year":sy,"cbro_issue_publication_year":iy,"chronology":("ISSUE_PRECEDES_SERIES_START" if sy and iy and int(iy)<int(sy) else "PLAUSIBLE_NOT_PROVEN" if sy and iy else "DATE_INCOMPLETE"),"cbro_data_id":right.get("checkbox_id",""),"cbh_url":left["url"],"cbro_url":right["url"]})
write("chronologie_series_vs_numeros.csv",chronology,["title_cbh","title_cbro","issue","cbh_series_start_year","cbro_issue_publication_year","chronology","cbro_data_id","cbh_url","cbro_url"])
print("CHRONOLOGY YEAR PAIRS",sum(x["chronology"]!="DATE_INCOMPLETE" for x in chronology),"IMPOSSIBLE",sum(x["chronology"]=="ISSUE_PRECEDES_SERIES_START" for x in chronology),flush=True)


# Group review candidates by series/volume pair, reducing hundreds of
# issue-level checks to a smaller set of explicit editorial decisions.
grouped=defaultdict(list)
for item in review:
 grouped[(item["title_cbh"],item["title_cbro"],item["cbh_url"],item["cbro_url"])].append(int(item["issue"]))
review_groups=[]
for (left,right,cbh_url,cbro_url),issues in sorted(grouped.items()):
 review_groups.append({"title_cbh":left,"title_cbro":right,"issue_count":len(set(issues)),"issue_numbers":", ".join(map(str,sorted(set(issues)))),"cbh_url":cbh_url,"cbro_url":cbro_url,"decision":"REVIEW_REQUIRED"})
write("groupes_a_verifier.csv",review_groups,["title_cbh","title_cbro","issue_count","issue_numbers","cbh_url","cbro_url","decision"])

# DATE SEMANTICS (user-confirmed):
# CBH dates attached to issue ranges (e.g. Iron Man #7-12 (Jun 06)) describe the range, NOT necessarily series launch.\n# Explicit series/volume launch years are a separate field and must not be inferred from range dates.
# CBRO year is the INDIVIDUAL ISSUE publication year.
# Never demand equality of these years or auto-reject a match because they differ.
# Series start year <= issue publication year is only a plausibility check,
# not sufficient evidence to mark progress.
# Evidence for volume adjudication: extract any explicit publication year,
# issue count and contiguous issue spans. A date not printed in the source
# must remain unknown rather than being guessed from reading-order position.
for group in review_groups:
 nums=[int(n) for n in group["issue_numbers"].split(", ") if n.isdigit()]
 group["first_issue"]=min(nums) if nums else ""
 group["last_issue"]=max(nums) if nums else ""
 group["contiguous"]=bool(nums and len(nums)==max(nums)-min(nums)+1)
 years=re.findall(r"\b(?:19|20)\d{2}\b",group["title_cbh"]+" "+group["title_cbro"])
 group["explicit_years"]=", ".join(sorted(set(years))) if years else "NOT_STATED"
 group["publication_date_verified"]="NO"
 group["match_confidence"]="PENDING_DATE_AND_VOLUME"
write("groupes_dates_et_chapitres.csv",review_groups,["title_cbh","title_cbro","issue_count","first_issue","last_issue","contiguous","explicit_years","publication_date_verified","match_confidence","cbh_url","cbro_url","issue_numbers","decision"])

print("REVIEW GROUPS",len(review_groups),flush=True)

# Deduplicate the same series pair across reading-order pages, retaining
# the union of issue numbers and source-page evidence for manual chronology checks.
series_pairs=defaultdict(lambda:{"issues":set(),"cbh_urls":set(),"cbro_urls":set()})
for item in review:
 key=(item["title_cbh"],item["title_cbro"])
 series_pairs[key]["issues"].add(int(item["issue"]))
 series_pairs[key]["cbh_urls"].add(item["cbh_url"])
 series_pairs[key]["cbro_urls"].add(item["cbro_url"])
series_report=[]
for (left,right),v in sorted(series_pairs.items()):
 nums=sorted(v["issues"])
 series_report.append({"title_cbh":left,"title_cbro":right,"issue_count":len(nums),"first_issue":nums[0],"last_issue":nums[-1],"issue_numbers":", ".join(map(str,nums)),"cbh_pages":len(v["cbh_urls"]),"cbro_pages":len(v["cbro_urls"]),"date_verification":"REQUIRED","decision":"DO_NOT_AUTO_MARK"})
write("series_a_verifier_sans_doublons.csv",series_report,["title_cbh","title_cbro","issue_count","first_issue","last_issue","issue_numbers","cbh_pages","cbro_pages","date_verification","decision"])

# Expose title/volume pairs that cannot be disambiguated by issue count alone.
# A matching issue number is not proof when multiple volume candidates exist.
volume_conflicts=[]
cbro_by_normalized=defaultdict(set)
for item in rows:
 if item["source"]=="CBRO":
  cbro_by_normalized[item["normalized"]].add(item["title"])
for item in series_report:
 variants=sorted(cbro_by_normalized.get(clean(item["title_cbh"]),set()))
 if len(variants)>1:
  volume_conflicts.append({"title_cbh":item["title_cbh"],"candidate_cbro_volumes":" | ".join(variants),"issue_numbers":item["issue_numbers"],"decision":"HOLD_UNTIL_PUBLICATION_YEAR_VERIFIED"})
write("conflits_volumes.csv",volume_conflicts,["title_cbh","candidate_cbro_volumes","issue_numbers","decision"])

# Quantify publication-year evidence collected from actual CBRO page text.
dated_rows=[x for x in rows if x["source"]=="CBRO" and x.get("publication_year")]
write("cbro_annees_observees.csv",dated_rows,fields)

# Confirm CBRO progress keys are unique per issue and available for JSON reconciliation.
keys=[x["checkbox_id"] for x in rows if x["source"]=="CBRO" and x.get("checkbox_id")]
key_collisions=defaultdict(list)
for x in rows:
 if x["source"]=="CBRO" and x.get("checkbox_id"):
  key_collisions[x["checkbox_id"]].append(x)
conflicts=[{"checkbox_id":key,"references":" | ".join(sorted(set(v["title"]+" #"+v["issue"] for v in values))),"occurrences":len(values)} for key,values in key_collisions.items() if len(set(v["title"]+" #"+v["issue"] for v in values))>1]
write("conflits_identifiants_cbro.csv",conflicts,["checkbox_id","references","occurrences"])
print("CBRO DATA-ID COVERAGE",len(keys),"COLLISIONS",len(conflicts),flush=True)

print("CBRO YEAR EVIDENCE (LABEL ONLY)",len(dated_rows),flush=True)


print("UNIQUE SERIES PAIRS",len(series_report),flush=True)



# Never treat the following as verified reading progress:
# titles normalized without volume identity; narrative recommendations;
# CBRO pages outside this limited selection; duplicated ranges.
report={"cbh_ordering_instructions":len(ordering_notes),"cbh_group_dates_extracted":sum(bool(x.get("cbh_group_date")) for x in rows if x["source"]=="CBH"),"cbh_series_start_year_evidence":sum(bool(x.get("series_start_year")) for x in rows if x["source"]=="CBH"),"chronology_year_pairs":sum(x["chronology"]!="DATE_INCOMPLETE" for x in chronology),"chronology_impossible":sum(x["chronology"]=="ISSUE_PRECEDES_SERIES_START" for x in chronology),"cbro_data_id_coverage":len(keys),"cbro_data_id_conflicts":len(conflicts),"cbro_publication_year_evidence":len(dated_rows),"volume_conflicts":len(volume_conflicts),"unique_series_pairs":len(series_report),"review_groups":len(review_groups),"identical_title_candidates":len(safe),"requires_review":len(review),"suspect_contexts":len(suspect),"unresolved_issues":len(unresolved),"scope_violations":scope_violations,"antman_stop_found":stop_found,"warning":"DIAGNOSTIC UNIQUEMENT. Volumes ignorés dans les rapprochements; recueils et événements non exhaustifs. Aucun JSON modifié.","pages":len(urls),"errors":errors,"diagnostics":diagnostics,"cbh_unique":len(a),"cbro_unique":len(b),"common_approximate":len(a.keys()&b.keys()),"cbh_only_approximate":len(a.keys()-b.keys()),"cbro_only_approximate":len(b.keys()-a.keys())}
(O/"bilan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2),flush=True)
if errors or scope_violations:raise SystemExit(2)
