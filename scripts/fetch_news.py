#!/usr/bin/env python3
"""Fetch permitted public RSS summaries; no article scraping or full-text copying."""
import datetime, html, json, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
FEEDS = [
 ('Geo Urdu','https://news.google.com/rss/search?q=site%3Aurdu.geo.tv+when%3A2d&hl=ur&gl=PK&ceid=PK%3Aur','National'),
 ('Express Urdu','https://www.express.pk/feed/','National'),
 ('Dunya Urdu','https://news.google.com/rss/search?q=site%3Aurdu.dunyanews.tv+when%3A2d&hl=ur&gl=PK&ceid=PK%3Aur','National'),
 ('BBC Urdu','https://feeds.bbci.co.uk/urdu/rss.xml','World'),
 ('BBC World','https://feeds.bbci.co.uk/news/world/rss.xml','World'),
 ('Arab News','https://www.arabnews.com/rss.xml','Middle East'),
 ('CNN','https://news.google.com/rss/search?q=site%3Acnn.com+when%3A2d&hl=en-US&gl=US&ceid=US%3Aen','World'),
 ('Sports Pakistan','https://news.google.com/rss/search?q=Pakistan+sports+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Sports'),
 ('Pakistan Economy','https://news.google.com/rss/search?q=Pakistan+economy+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Economy'),
 ('Pakistan Crime','https://news.google.com/rss/search?q=Pakistan+crime+when%3A2d&hl=en&gl=PK&ceid=PK%3Aen','Crime'),
]
def txt(node,tag):
 el=node.find(tag)
 return ''.join(el.itertext()).strip() if el is not None else ''
def clean(s):
 return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',s or ''))).strip()[:600]
def get_photo(item):
 # RSS enclosure, media:content, media:thumbnail, or a directly embedded image.
 media='{http://search.yahoo.com/mrss/}'
 candidates=[]
 for tag in (media+'content',media+'thumbnail','enclosure'):
  for node in item.findall(tag):
   url=node.get('url','')
   typ=node.get('type','')
   if tag=='enclosure' and typ and not typ.startswith('image/'):continue
   candidates.append(url)
 for field in ('description','{http://purl.org/rss/1.0/modules/content/}encoded'):
  raw=txt(item,field)
  candidates += re.findall(r'<img[^>]+src=["\']([^"\']+)',raw,re.I)
 for url in candidates:
  url=html.unescape(url).strip()
  if url.startswith('https://') and not re.search(r'\.(svg|gif)(?:[?#]|$)',url,re.I):return url[:1200]
 return ''

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
   result.append(dict(title=title,link=link,description=summary,source=source,cat=category,date=date,photo=get_photo(el)))
 return result
# Source preference is used within each category. No category is filled with unrelated news.
QUOTAS={'National':10,'Economy':5,'Crime':5,'Sports':5,'World':4,'Middle East':4,'Strange':2}
PRIORITY=['Geo Urdu','Express Urdu','Dunya Urdu','BBC Urdu','BBC World','Arab News','CNN']
import hashlib

def classify(item):
 title=(item['title']+' '+item.get('description','')).lower()
 source=item['source']
 pakistan=any(k in title for k in ('پاکستان','پاکستانی','کراچی','لاہور','اسلام آباد','پشاور','کوئٹہ','ملتان','پنجاب','سندھ','بلوچستان','خیبر','pakistan','pakistani','karachi','lahore','islamabad','punjab','sindh','balochistan','peshawar'))
 middle=any(k in title for k in ('غزہ','فلسطین','اسرائیل','ایران','سعودی','لبنان','شام','یمن','قطر','دبئی','عرب امارات','gaza','israel','iran','saudi','palestin','lebanon','syria','yemen','qatar','uae','middle east'))
 if any(k in title for k in ('عجیب','انوکھ','حیران کن','دلچسپ','نایاب','strange','bizarre','unusual','oddity')):return 'Strange'
 if pakistan and any(k in title for k in ('کرکٹ','فٹبال','ہاکی','ٹیسٹ میچ','پی ایس ایل','کھلاڑی','کھیل','sports','cricket','football','psl','hockey','match')):return 'Sports'
 if pakistan and any(k in title for k in ('قتل','اغوا','ڈکیتی','چوری','پولیس','گرفتار','جرم','ملزم','crime','murder','police','arrest','robbery','kidnap')):return 'Crime'
 if pakistan and any(k in title for k in ('معیشت','روپے','ڈالر','مہنگائی','اسٹاک','بجٹ','ٹیکس','قیمت','برآمد','درآمد','آئی ایم ایف','economy','economic','inflation','rupee','stock','budget','tax','imf','exports')):return 'Economy'
 if middle:return 'Middle East'
 if pakistan:return 'National'
 return 'World'

def main():
 all_items=[]; status=[];seen=set()
 for source,url,category in FEEDS:
  try:
   fetched=fetch(source,url,category);added=0
   for item in fetched:
    # Avoid duplicate URLs and very similar titles across publishers.
    normalized=re.sub(r'[^\w\u0600-\u06ff]+','',item['title'].lower())[:110]
    key=item['link'].split('?')[0].rstrip('/')
    if key in seen or normalized in seen:continue
    seen.add(key);seen.add(normalized);item['cat']=classify(item);all_items.append(item);added+=1
   status.append({'source':source,'added':added,'ok':True})
  except Exception as e:status.append({'source':source,'added':0,'ok':False,'error':str(e)[:160]})
  time.sleep(.25)
 def rank(item):
  try:return PRIORITY.index(item['source'])
  except ValueError:return len(PRIORITY)
 buckets={c:[] for c in QUOTAS}
 for item in sorted(all_items,key=rank):
  if item['cat'] in buckets:buckets[item['cat']].append(item)
 picked=[]; shortages={}
 for category,quota in QUOTAS.items():
  group=buckets[category][:quota]
  picked.extend(group)
  if len(group)<quota:shortages[category]=quota-len(group)
 output={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':len(picked),'target':40,'quotas':QUOTAS,'shortages':shortages,'items':picked,'sources':status}
 Path('news').mkdir(exist_ok=True)
 Path('news/latest.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Saved',len(picked),'of 40 unique headlines; shortages:',shortages)
if __name__=='__main__':main()
