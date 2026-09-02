#!/usr/bin/env python3
"""Extract recent article links from direct publisher section pages."""
from __future__ import annotations
import argparse, html, json, re, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA = "Mozilla/5.0 (compatible; NRW-Lagebild/1.0)"
SECTIONS = {
  "Köln/Bonn": ["https://www1.wdr.de/nrw/koeln/index.html", "https://www1.wdr.de/nrw/rheinland/index.html"],
  "Düsseldorf/Niederrhein": ["https://www1.wdr.de/nrw/duesseldorf/index.html"],
  "Ruhrgebiet": ["https://www1.wdr.de/nrw/ruhrgebiet/index.html", "https://www1.wdr.de/nrw/dortmund/index.html", "https://www1.wdr.de/nrw/essen/index.html"],
  "Münsterland": ["https://www1.wdr.de/nrw/muensterland/index.html"],
  "Ostwestfalen-Lippe": ["https://www1.wdr.de/nrw/ostwestfalen-lippe/index.html"],
  "Aachen/Eifel": ["https://www1.wdr.de/nrw/aachen-eifel/index.html"],
  "Südwestfalen": ["https://www1.wdr.de/nrw/sauerland-siegerland/index.html"],
  "Landespolitik": ["https://www1.wdr.de/politik/politik-in-nrw/index.html"],
}

class Links(HTMLParser):
  def __init__(self, base): super().__init__(); self.base=base; self.a=None; self.out=[]
  def handle_starttag(self, tag, attrs):
    if tag == "a":
      d=dict(attrs); href=d.get("href","")
      if href: self.a={"url":urllib.parse.urljoin(self.base,href),"text":[]}
  def handle_data(self, data):
    if self.a: self.a["text"].append(data)
  def handle_endtag(self, tag):
    if tag=="a" and self.a:
      self.a["title"]=re.sub(r"\s+"," ",html.unescape(" ".join(self.a.pop("text")))).strip()
      if self.a["title"] and self.a["url"].startswith("https://www1.wdr.de/"): self.out.append(self.a)
      self.a=None

def main():
  p=argparse.ArgumentParser(); p.add_argument("--output",default="data/wdr_sections.json"); a=p.parse_args()
  result=[]; errors=[]
  for region,urls in SECTIONS.items():
    for url in urls:
      try:
        req=urllib.request.Request(url,headers={"User-Agent":UA})
        text=urllib.request.urlopen(req,timeout=20).read(2_000_000).decode("utf-8","replace")
        parser=Links(url); parser.feed(text)
        seen=set()
        for x in parser.out:
          if x["url"] in seen or len(x["title"])<18: continue
          seen.add(x["url"]); x["region"]=region; x["section"]=url; result.append(x)
      except Exception as e: errors.append({"url":url,"error":f"{type(e).__name__}: {e}"})
  Path(a.output).parent.mkdir(parents=True,exist_ok=True)
  Path(a.output).write_text(json.dumps({"links":result,"errors":errors},ensure_ascii=False,indent=2)+"\n")
  print(json.dumps({"links":len(result),"errors":errors},ensure_ascii=False))
if __name__=="__main__": main()
