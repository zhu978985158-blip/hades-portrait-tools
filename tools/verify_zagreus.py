# coding: utf-8
from pathlib import Path
import sys,json,hashlib
sys.path[:0]=[str(Path(__file__).parent/'deppth-master'),str(Path(__file__).parent/'deps')]
from deppth.sggpio import PackageWithManifestReader
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parent.parent;B=ROOT/'packages/zagreus'; targets={p.stem for p in (ROOT/'inputs/zagreus').glob('*.png')};report=[]
for rel in [Path(v)/p for v in ['', 'BC3','720p'] for p in ['GUI.pkg','DeathArea.pkg']]:
 with PackageWithManifestReader(str(B/'原版备份'/rel)) as f:
  original={e.name:hashlib.sha256(e.data).hexdigest() for e in f}
  oldlist=[s for a in f.manifest.values() for s in a.subAtlases]
  oldsprites={s['name']:s for s in oldlist}
 with PackageWithManifestReader(str(B/'安装资源'/rel)) as f:
  updated={}; newcount=0
  for e in f:
   updated[e.name]=hashlib.sha256(e.data).hexdigest()
   if e.name not in original:
    im=e._get_image();s=e.manifest_entry.subAtlases[0];r=s['rect'];im=im.crop((r['x'],r['y'],r['x']+r['width'],r['y']+r['height']));name=s['name'].split('\\')[-1]
    assert im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255)
    if len(rel.parts)==1:
     ref=Image.open(B/'适配预览'/(name+'.png')); assert ref.size==im.size and ref.tobytes()==im.tobytes()
    newcount+=1
  sprites=[s for a in f.manifest.values() for s in a.subAtlases];new={s['name']:s for s in sprites}
  from collections import Counter
  assert Counter(s['name'] for s in oldlist)==Counter(s['name'] for s in sprites),'Sprite multiplicities changed'
  oldother=Counter(json.dumps(s,sort_keys=True) for s in oldlist if s['name'].split('\\')[-1] not in targets)
  newother=Counter(json.dumps(s,sort_keys=True) for s in sprites if s['name'].split('\\')[-1] not in targets)
  assert oldother==newother,'Unrelated sprite metadata changed'
  assert set(oldsprites)==set(new),'Missing/added sprite references'
  assert all(updated[n]==h for n,h in original.items()),'Original texture changed'
  assert all(s==new[n] for n,s in oldsprites.items() if n.split('\\')[-1] not in targets),'Unrelated metadata changed'
  assert newcount==(9 if rel.name=='GUI.pkg' else 1)
  report.append(dict(package=str(rel),original_textures_unchanged=len(original),sprite_names_preserved=len(new),replaced=newcount,status='PASS'))
(B/'静态验收.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Display premultiplied textures correctly in the contact sheet.
arts=list((B/'适配预览').glob('*.png')); sheet=Image.new('RGB',(1500,1000),(50,52,55));d=ImageDraw.Draw(sheet)
for i,p in enumerate(arts):
 im=Image.open(p);im=Image.frombytes('RGBa',im.size,im.tobytes()).convert('RGBA');im.thumbnail((280,440));x=i%5*300+(300-im.width)//2;y=i//5*500+10;sheet.paste(im,(x,y),im);d.text((i%5*300+5,y+455),p.stem.replace('Portraits_Zagreus','Zag'),fill='white')
sheet.save(B/'适配总览.jpg');print(json.dumps(report,ensure_ascii=False))
