from pathlib import Path
import os
import sys, json, copy, hashlib, shutil, struct
from collections import Counter
from PIL import Image
sys.path[:0]=[str(Path(__file__).parent/'deppth-master'),str(Path(__file__).parent/'deps')]
from deppth.sggpio import PackageWithManifestReader,PackageWriter
from deppth.entries import TextureEntry
ROOT=Path(__file__).resolve().parent.parent
SRC=Path(os.environ.get('HADES_PACKAGES_DIR', str(Path.home()/'Library/Application Support/Steam/steamapps/common/Hades/Game.macOS.app/Contents/Resources/Content/macOS/Packages')))
B=ROOT/'packages/zeus';BACK=B/'安装前备份';PATCH=B/'安装资源';ART=B/'适配预览'
for d in (BACK,PATCH,ART):d.mkdir(parents=True,exist_ok=True)
inputs={'Portraits_Zeus_01':'Portraits_Zeus_01_透明.png','CodexPortrait_Zeus':'CodexPortrait_Zeus.png','Zeus_Hades_Handshake_02':'Zeus_Hades_Handshake_02.png'}
images={n:Image.open(ROOT/'inputs/zeus'/p).convert('RGBA') for n,p in inputs.items()}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]; reports=[]; records=[]
for variant in ('','BC3','720p'):
 rel=Path(variant)/'GUI.pkg';source=SRC/rel;target=PATCH/rel;target.parent.mkdir(parents=True,exist_ok=True)
 for p in (source,Path(str(source)+'_manifest')):
  b=BACK/p.relative_to(SRC);b.parent.mkdir(parents=True,exist_ok=True)
  if not b.exists():shutil.copy2(p,b)
  assert sha(b)==sha(p),'Source differs from backup'
 newmanifest=[];added=[];expected={};oldtextures={};oldsprites=[]
 with PackageWithManifestReader(str(source)) as reader,PackageWriter(str(target),compressor=reader.compressor,version=reader.version) as writer:
  for entry in reader:
   writer.write_entry(entry);oldtextures[entry.name]=hashlib.sha256(entry.data).hexdigest()
   a=entry.manifest_entry
   if a is None:continue
   a=copy.deepcopy(a);remaining=[]
   for s in a.subAtlases:
    oldsprites.append(copy.deepcopy(s));name=s['name'].split('\\')[-1]
    if name not in images:remaining.append(s);continue
    sz=(s['rect']['width'],s['rect']['height'])
    # Source PNG is straight alpha. Hades textures use premultiplied alpha.
    pm=images[name].convert('RGBa').resize(sz,Image.Resampling.LANCZOS)
    art=Image.frombytes('RGBA',sz,pm.tobytes())
    preview=pm.convert('RGBA');dest=ART/(variant or '默认高清');dest.mkdir(exist_ok=True);preview.save(dest/(name+'.png'))
    newname=a.name.rsplit('\\',1)[0]+'\\ZeusCustom_'+name
    padded=Image.new('RGBA',(sz[0]+2,sz[1]+2));padded.paste(art,(1,1))
    t=TextureEntry();t.name=newname;t.data=t._create_inner_xnb(padded);t.data=b'XNBw\x06\x00'+struct.pack('<I',len(t.data)+10)+t.data;t.size=len(t.data)
    na=copy.deepcopy(a);na.name=newname;na.referencedTextureName=newname;na.isReference=True
    ns=copy.deepcopy(s);ns['rect']=dict(x=1,y=1,width=sz[0],height=sz[1]);ns['hull']=[];na.subAtlases=[ns]
    added.append((t,na));expected[newname]=art
    records.append(dict(variant=variant or '默认高清',name=name,old=s,new=ns,alpha='premultiplied'))
   a.subAtlases=remaining
   if remaining:newmanifest.append(a)
  assert len(added)==3
  for t,a in added:writer.write_entry(t);newmanifest.append(a)
 with PackageWriter(str(target)+'_manifest',version=7,is_manifest=True) as writer:
  for a in newmanifest:writer.write_entry(a)
 with PackageWithManifestReader(str(target)) as reader:
  textures={};newcount=0
  for e in reader:
   textures[e.name]=hashlib.sha256(e.data).hexdigest()
   if e.name in expected:
    im=e._get_image();r=e.manifest_entry.subAtlases[0]['rect'];im=im.crop((1,1,1+r['width'],1+r['height']))
    assert im.tobytes()==expected[e.name].tobytes();newcount+=1
  newsprites=[s for a in reader.manifest.values() for s in a.subAtlases]
  assert Counter(s['name'] for s in oldsprites)==Counter(s['name'] for s in newsprites)
  def unrelated(seq):return Counter(json.dumps(s,sort_keys=True) for s in seq if s['name'].split('\\')[-1] not in images)
  assert unrelated(oldsprites)==unrelated(newsprites)
  assert all(textures[n]==h for n,h in oldtextures.items())
  assert newcount==3
 reports.append(dict(package=str(rel),replaced=3,original_textures_unchanged=len(oldtextures),sprite_names_preserved=len(newsprites),pixel_readback='PASS',unrelated_metadata='PASS'))
 for p in (target,Path(str(target)+'_manifest')):
  r=p.relative_to(PATCH);assert sha(SRC/r)==sha(BACK/r)
  rows.append(dict(path=str(r),original_sha256=sha(BACK/r),replacement_sha256=sha(p),bytes=p.stat().st_size))
 print('Verified',rel,flush=True)
(B/'安装清单.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
(B/'静态验收.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
(B/'适配记录.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('PASS: 9 assets, 6 files. Existing modifications preserved.')
