# coding: utf-8
from pathlib import Path
import os
import sys,json,copy,hashlib,shutil
import numpy as np
from PIL import Image,ImageDraw
sys.path[:0]=[str(Path(__file__).parent/'deppth-master'),str(Path(__file__).parent/'deps')]
from deppth.sggpio import PackageWithManifestReader,PackageWriter
from deppth.entries import TextureEntry
ROOT=Path(__file__).resolve().parent.parent
SRC=Path(os.environ.get('HADES_PACKAGES_DIR', str(Path.home()/'Library/Application Support/Steam/steamapps/common/Hades/Game.macOS.app/Contents/Resources/Content/macOS/Packages')))
BUILD=ROOT/'packages/zagreus'; BUILD.mkdir(exist_ok=True)
BACK=BUILD/'原版备份'; PATCH=BUILD/'安装资源'; ART=BUILD/'适配预览'
for d in [BACK,PATCH,ART]:d.mkdir(exist_ok=True)
INPUT=ROOT/'inputs/zagreus'
names={p.stem for p in INPUT.glob('*.png')}
records=[]; files=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resize_pm(im,sz):
 # Inputs empirically carry premultiplied RGB. Resample channels in that space.
 return Image.frombytes('RGBA',sz,Image.frombytes('RGBa',im.size,im.tobytes()).resize(sz,Image.Resampling.LANCZOS).tobytes())
def fit(im,size):
 ratio=min(size[0]/im.width,size[1]/im.height); sz=(max(1,round(im.width*ratio)),max(1,round(im.height*ratio)))
 out=Image.new('RGBA',size);out.paste(resize_pm(im,sz),((size[0]-sz[0])//2,(size[1]-sz[1])//2));return out
# Cache full-resolution replacements in original canvas coordinates.
meta=json.loads((INPUT/'原版相关静态资源.json').read_text())
master={}
for m in meta:
 name=m['name'].split('\\')[-1]
 if name not in names:continue
 im=Image.open(INPUT/(name+'.png')).convert('RGBA')
 if name.startswith('Portraits_Zagreus'):
  size=(1002,1107);out=Image.new('RGBA',size)
  scaled=resize_pm(im,(939,1037));out.paste(scaled,(31,70))
  master[name]=(out,dict(x=0,y=0),dict(x=1002,y=1107),dict(x=1.,y=1.))
 else:
  crop=im.crop(im.getchannel('A').getbbox())
  size=(m['rect']['width'],m['rect']['height']);out=fit(crop,size)
  master[name]=(out,m['topLeft'],m['originalSize'],m['scaleRatio'])
 out.save(ART/(name+'.png'))
for variant in ['', 'BC3','720p']:
 for base in ['GUI.pkg','DeathArea.pkg']:
  rel=Path(variant)/base; source=SRC/rel; target=PATCH/rel;target.parent.mkdir(parents=True,exist_ok=True)
  for p in [source,Path(str(source)+'_manifest')]:
   b=BACK/p.relative_to(SRC);b.parent.mkdir(parents=True,exist_ok=True)
   if not b.exists():shutil.copy2(p,b)
   assert digest(b)==digest(p),'Original differs from backup'
  manifest_new=[]; appended=[]; changed=[]
  with PackageWithManifestReader(str(source)) as reader,PackageWriter(str(target),compressor=reader.compressor,version=reader.version) as writer:
   print('BUILD',rel,flush=True)
   for entry in reader:
    writer.write_entry(entry) # Preserve all original texture payloads unchanged.
    a=entry.manifest_entry
    if a is None:continue
    a=copy.deepcopy(a); remaining=[]
    for s in a.subAtlases:
     name=s['name'].split('\\')[-1]
     if name not in master:remaining.append(s);continue
     full,tl,orig,ratio=master[name]
     if variant:
      if name.startswith('Portraits_Zagreus'):
       factor=1/s['scaleRatio']['x']; size=(round(1002*factor),round(1107*factor)); art=resize_pm(full,size)
       sr=dict(x=1002/size[0],y=1107/size[1]);topleft=dict(x=0,y=0)
      else:
       size=(s['rect']['width'],s['rect']['height']); art=resize_pm(full,size);sr=s['scaleRatio'];topleft=s['topLeft']
     else:art=full;sr=ratio;topleft=tl
     newname=a.name.rsplit('\\',1)[0]+'\\ZagStatic_'+name
     image=Image.new('RGBA',(art.width+2,art.height+2));image.paste(art,(1,1))
     # One transparent pixel gutter prevents sampling neighboring sprites.
     texture=TextureEntry();texture.name=newname
     texture.data=texture._create_inner_xnb(image)
     import struct
     texture.data=b'XNBw\x06\x00'+struct.pack('<I',len(texture.data)+10)+texture.data;texture.size=len(texture.data)
     newatlas=copy.deepcopy(a);newatlas.name=newname;newatlas.referencedTextureName=newname;newatlas.isReference=True
     item=copy.deepcopy(s);item.update(rect=dict(x=1,y=1,width=art.width,height=art.height),topLeft=topleft,originalSize=orig,scaleRatio=sr,hull=[])
     newatlas.subAtlases=[item]; appended.append((texture,newatlas));changed.append(s['name'])
     records.append(dict(variant=variant or '默认',package=base,name=name,old=s,new=item,atlas=newname))
    a.subAtlases=remaining
    if remaining:manifest_new.append(a)
   for t,a in appended:writer.write_entry(t);manifest_new.append(a)
  with PackageWriter(str(target)+'_manifest',version=7,is_manifest=True) as writer:
   for a in manifest_new:writer.write_entry(a)
  for p in [target,Path(str(target)+'_manifest')]:
   r=p.relative_to(PATCH); files.append(dict(path=str(r),original_sha256=digest(BACK/r),replacement_sha256=digest(p),bytes=p.stat().st_size))
  assert len(changed)==(9 if base=='GUI.pkg' else 1)
(BUILD/'安装清单.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
(BUILD/'适配记录.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('BUILT',len(records),'sprite replacements')
