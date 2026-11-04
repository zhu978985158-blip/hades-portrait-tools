# coding: utf-8
from pathlib import Path
import sys,json,hashlib,shutil,os,subprocess
B=Path(__file__).resolve().parent
GAME=Path(os.environ.get('HADES_PACKAGES_DIR', str(Path.home()/'Library/Application Support/Steam/steamapps/common/Hades/Game.macOS.app/Contents/Resources/Content/macOS/Packages')))
rows=json.loads((B/'安装清单.json').read_text())
mode=sys.argv[1] if len(sys.argv)>1 else 'check'
assert mode in ('install','restore','check')
def destination(row):
 package_path=Path(row['path'])
 assert not package_path.is_absolute() and '..' not in package_path.parts, '安装清单包含非法路径'
 root=GAME.parent.parent if 'content_path' in row else GAME
 relative=Path(row.get('content_path',row['path']))
 assert not relative.is_absolute() and '..' not in relative.parts, '安装清单包含非法目标路径'
 target=root/relative
 assert target.resolve().is_relative_to(root.resolve()), '安装目标越出游戏目录'
 return target
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if mode!='check':
 processes=subprocess.run(['/bin/ps','-axo','comm'],capture_output=True,text=True,check=True).stdout
 if any('Game.macOS.app/Contents/MacOS/' in s or '/Hades/' in s for s in processes.splitlines()):
  raise SystemExit('请先完全退出 Hades，再运行安装或恢复。')
 for row in rows:
  current=sha(destination(row));assert current in (row['original_sha256'],row['replacement_sha256']),'游戏文件版本已变化，请勿强行覆盖：'+row['path']
  assert sha(B/'安装前备份'/row['path'])==row['original_sha256']
  assert sha(B/'安装资源'/row['path'])==row['replacement_sha256']
 staged=[];done=[]
 try:
  for row in rows:
   target=destination(row);src=B/('安装资源' if mode=='install' else '安装前备份')/row['path']
   temp=target.with_name(target.name+'.zeus-staging')
   assert not temp.exists(),'存在未完成的暂存文件：'+str(temp)
   shutil.copy2(src,temp);assert sha(temp)==sha(src);staged.append((temp,target,row,sha(target)))
  for temp,target,row,oldhash in staged:
   os.replace(temp,target);done.append((target,row,oldhash))
  for row in rows:assert sha(destination(row))==row['replacement_sha256' if mode=='install' else 'original_sha256']
 except Exception:
  for target,row,oldhash in reversed(done):
   src=B/('安装前备份' if oldhash==row['original_sha256'] else '安装资源')/row['path'];shutil.copy2(src,target)
  for temp,_,_,_ in staged:
   if temp.exists():temp.unlink()
  raise
status=[dict(path=r['path'],state=('replacement' if sha(destination(r))==r['replacement_sha256'] else 'original' if sha(destination(r))==r['original_sha256'] else 'unknown')) for r in rows]
(B/'当前安装状态.json').write_text(json.dumps(dict(action=mode,files=status),ensure_ascii=False,indent=2))
print(json.dumps(status,ensure_ascii=False,indent=2))
