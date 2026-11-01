#!/usr/bin/env python3
"""Fetch permitted public RSS summaries; no article scraping or full-text copying."""
import datetime, html, json, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
FEEDS = [
 ('BBC Urdu','https://feeds.bbci.co.uk/urdu/rss.xml','World'),
 ('BBC World','https://feeds.bbci.co.uk/news/world/rss.xml','World'),
 ('Express Urdu','https://www.express.pk/feed/','National'),
 ('Arab News','https://www.arabnews.com/rss.xml','Middle East'),
 ('CNN','https://news.google.com/rss/search?q=site%3Acnn.com+when%3A2d&hl=en-US&gl=US&ceid=US%3Aen','World'),
 ('Geo Urdu','https://news.google.com/rss/search?q=site%3Aurdu.geo.tv+when%3A2d&hl=ur&gl=PK&ceid=PK%3Aur','National'),
 ('Dunya Urdu','https://news.google.com/rss/search?q=site%3Aurdu.dunyanews.tv+when%3A2d&hl=ur&gl=PK&ceid=PK%3Aur','National'),
 ('Sports Pakistan','https://news.google.com/rss/search?q=Pakistan+sports+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Sports'),
 ('Pakistan Economy','https://news.google.com/rss/search?q=Pakistan+economy+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Economy'),
 ('Pakistan Crime','https://news.google.com/rss/search?q=Pakistan+crime+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Crime'),
]
def txt(node,tag):
 el=node.find(tag)
 return ''.join(el.itertext()).strip() if el is not None else ''
def clean(s):
 return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',s or ''))).strip()[:600]
def fetch(source,url,category):
 req=urllib.request.Request(url,headers={'User-Agent':'AGAHI-News-Studio/1.0 (RSS reader)','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
 with urllib.request.urlopen(req,timeout=18) as resp: data=resp.read(2_000_000)
 root=ET.fromstring(data)
 items=root.findall('.//item')
 if not items: items=root.findall('{http://www.w3.org/2005/Atom}entry')
 result=[]
 for el in items[:35]:
  title=clean(txt(el,'title') or txt(el,'{http://www.w3.org/2005/Atom}title'))
  link=txt(el,'link')
  if not link:
   a=el.find('{http://www.w3.org/2005/Atom}link');link=a.get('href','') if a is not None else ''
  summary=clean(txt(el,'description') or txt(el,'{http://www.w3.org/2005/Atom}summary'))
  date=txt(el,'pubDate') or txt(el,'{http://www.w3.org/2005/Atom}published')
  if title and link.startswith(('https://','http://')):
   result.append(dict(title=title,link=link,description=summary,source=source,cat=category,date=date))
 return result
def main():
 items=[]; seen=set(); status=[]
 for source,url,category in FEEDS:
  try:
   news=fetch(source,url,category)
   count=0
   for item in news:
    key=item['link'].split('?')[0]
    if key not in seen:seen.add(key);items.append(item);count+=1
   status.append({'source':source,'added':count,'ok':True})
  except Exception as e:
   status.append({'source':source,'added':0,'ok':False,'error':str(e)[:160]})
  time.sleep(.25)
 output={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':len(items),'items':items[:240],'sources':status}
 Path('news').mkdir(exist_ok=True)
 Path('news/latest.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Saved',output['count'],'headlines; successful sources:',sum(x['ok'] for x in status))
if __name__=='__main__':main()
