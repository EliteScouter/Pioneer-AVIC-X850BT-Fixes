#!/usr/bin/env python3
"""Build unofficial 1.07ES from the untouched Pioneer EU130 1.06 package.

Windows + Python 3.10+ + makecab.exe. No pip packages required.
Usage: python tools/build.py ORIGINAL_AVICX850 NEW_OUTPUT_FOLDER --work WORK_FOLDER
"""
import argparse,hashlib,json,shutil,struct,zlib
from pathlib import Path
import pioneer_fw
import firmware_resources as resources

VERSION=0x01070000
PATCHES=[(0x195cbfc,'2088','1800'),(0x195ccf6,'fddf','fedf'),
 (0x195f0b6,'2088','1800'),(0x195f1b6,'fddf','fedf'),
 (0x1961fe8,'2088','1800'),(0x1961ffe,'fddf','fedf')]
sha=lambda b:hashlib.sha256(b).hexdigest()

def set_manifest_version(path):
    b=bytearray(path.read_bytes());struct.pack_into('<I',b,8,VERSION)
    if any(b[0x18:0x2c]):struct.pack_into('<I',b,0x20,VERSION)
    struct.pack_into('<I',b,len(b)-4,zlib.crc32(b[:-4]))
    path.write_bytes(b)

def public_caption(plain):
    old='Version %s\0'.encode('utf-16le')
    new='Ver 1.07ES\0'.encode('utf-16le')
    assert len(old)==len(new) and plain.count(old)==1
    assert plain.index(old)==0x1d0140
    return plain.replace(old,new)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args()
    assert not a.output.exists(),'Choose a new output directory'
    a.work.mkdir(parents=True,exist_ok=True)
    pp=Path('PLATFORM/EU130PLT.PRG')
    original=(a.original/pp).read_bytes()
    assert len(original)==49876544 and zlib.crc32(original)==0x969f60f1,'Requires original EU130 1.06 PRG'
    assert pioneer_fw.cmd_verify(type('A',(),{'root':str(a.original)}))==0
    shutil.copytree(a.original,a.output)
    prg=bytearray(original)
    for off,old,new in PATCHES:
        assert prg[off:off+2]==bytes.fromhex(old)
        prg[off:off+2]=bytes.fromhex(new)
    allowed=[(8,16),(0x1fc,0x200)]+[(o,o+2) for o,_,_ in PATCHES]
    compression={}
    for name,transform in [('layoutCreators.dat',resources.patch_layout),('initDB.dat',public_caption)]:
        entry,real,comp,start=resources.file_entry(prg,name)
        data=bytes(prg[start:start+comp]);plain=resources.decode_ce(data,real)
        modified=transform(plain)
        work=a.work/name;work.mkdir(exist_ok=True)
        encoded,pages=resources.ce_replace_pages(data,plain,modified,work)
        assert len(encoded)<=comp,'Resource must fit original slot'
        prg[start:start+comp]=encoded+b'\xff'*(comp-len(encoded))
        struct.pack_into('<II',prg,entry+12,len(modified),len(encoded))
        _,rr,cc,ss=resources.file_entry(prg,name)
        assert resources.decode_ce(bytes(prg[ss:ss+cc]),rr)==modified
        allowed.extend([(start,start+comp),(entry+12,entry+20)])
        compression[name]={'changed_semantic_pages':pages,'old_bytes':comp,'new_bytes':len(encoded),'round_trip':'PASS'}
    struct.pack_into('<I',prg,12,VERSION)
    (a.output/pp).write_bytes(prg)
    pioneer_fw.fix_prg(str(a.output/pp),str(a.output/pp))
    archive=Path('APL/Resource/Mame/image.iarc')
    asset=(Path(__file__).resolve().parents[1]/'assets/av-background.bmp').read_bytes()
    rgb=list(zip(asset[54::3],asset[55::3],asset[56::3]))
    assert len(rgb)==680*483 and all(min(c)>=8 for c in rgb)
    assert all(not(b&7 or g&3 or r&7) for b,g,r in rgb)
    image,target=resources.patch_archive((a.original/archive).read_bytes(),asset)
    (a.output/archive).write_bytes(image)
    for name in ['EU130APL.VER','EU130PLT.VER']:
        p=a.output/name
        p.write_bytes(pioneer_fw.build_ver(pioneer_fw.parse_ver(p.read_bytes()),str(a.output)))
        set_manifest_version(p)
    assert pioneer_fw.cmd_verify(type('A',(),{'root':str(a.output)}))==0
    final=(a.output/pp).read_bytes()
    assert len(original)==len(final)
    assert all(x==y or any(lo<=i<hi for lo,hi in allowed) for i,(x,y) in enumerate(zip(original,final)))
    changed=[p.relative_to(a.original).as_posix() for p in a.original.rglob('*') if p.is_file() and p.read_bytes()!=(a.output/p.relative_to(a.original)).read_bytes()]
    assert set(changed)=={'PLATFORM/EU130PLT.PRG','APL/Resource/Mame/image.iarc','EU130APL.VER','EU130PLT.VER'}
    report={'release':'1.07ES','numeric_update_version':'0x01070000','hardware_tested_this_exact_release':False,
      'feature_baseline':'User confirmed Bluetooth metadata, enlarged text and artifact-free palette on private 1.12',
      'popup':'English caption Version %s -> Ver 1.07ES; runtime version data unchanged; hardware confirmation pending',
      'background':'charcoal/red, no STi logo; all channel values >= 8',
      'RGB555_transparent_black_pixels':sum(1 for b,g,r in rgb if max(b,g,r)<8),
      'resource_compression':compression,'allowed_PRG_range_audit':'PASS','changed_files':changed,
      'original_PRG_sha256':sha(original),'PRG_sha256':sha(final),'image_iarc_sha256':sha(image)}
    (a.work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
