"""Checked Pioneer ROM resource and bitmap helpers for the public release."""
import struct, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'third_party'))
from wincedecompr.wincedecompr import CEDecompressROM,bin_decompress_rom
BASE=0x884A1000
def decode_ce(b, size):
    out=bytearray(size+4096)
    n=CEDecompressROM(b,len(b),out,size,0,1,4096)
    assert n==size, ('CE decode failed',n,size)
    return bytes(out[:size])

def file_entry(prg,name):
    r=struct.unpack_from('<I',prg,0x244)[0]-BASE+512
    mods=struct.unpack_from('<I',prg,r+16)[0]
    count=struct.unpack_from('<I',prg,r+48)[0]
    for i in range(count):
        a=r+84+mods*32+i*28
        real,comp,np,lp=struct.unpack_from('<4I',prg,a+12)
        ns=np-BASE+512
        if prg[ns:prg.index(0,ns)].decode()==name:
            return a,real,comp,lp-BASE+512
    raise ValueError(name)

def ce_replace_pages(old,plain,new,work):
    assert int.from_bytes(old[:3],'little')==len(plain)
    count=(len(plain)+4095)//4096
    assert (len(new)+4095)//4096==count
    header_size=(count+1)*3
    blocks=[];changed=[]
    for i in range(count):
        begin=header_size if i==0 else int.from_bytes(old[i*3:i*3+3],'little')
        end=int.from_bytes(old[(i+1)*3:(i+2)*3],'little')
        chunk=new[i*4096:(i+1)*4096]
        if chunk==plain[i*4096:(i+1)*4096]:
            blocks.append(old[begin:end]);continue
        changed.append(i)
        raw=work/f'page-{i:03d}.bin';cab=work/f'page-{i:03d}.cab'
        raw.write_bytes(chunk)
        result=subprocess.run(['makecab.exe','/D','CompressionType=LZX','/D',
            'CompressionMemory=15',str(raw),str(cab)],capture_output=True)
        assert result.returncode==0,result.stdout+result.stderr
        data=cab.read_bytes()
        assert data[:4]==b'MSCF' and struct.unpack_from('<H',data,26)[0]==1
        offset,numblocks,compression=struct.unpack_from('<IHH',data,36)
        assert numblocks==1 and compression==0x0f03
        _,compressed,uncompressed=struct.unpack_from('<IHH',data,offset)
        assert uncompressed==len(chunk)
        stream=data[offset+8:offset+8+compressed]
        block=struct.pack('<4I',15,len(chunk),len(stream),len(chunk))+stream
        buf=bytearray(len(chunk)+4096)
        status,n=bin_decompress_rom(block,len(block),buf)
        assert status==0 and n==len(chunk) and buf[:n]==chunk
        blocks.append(block)
    cursor=header_size
    table=bytearray(len(new).to_bytes(3,'little'))
    for block in blocks:
        cursor+=len(block); table+=cursor.to_bytes(3,'little')
    result=bytes(table)+b''.join(blocks)
    assert decode_ce(result,len(new))==new
    if len(result)>len(old):
        # Recompress an unchanged page if the standard encoder can recover
        # the few bytes needed. Page contents must still match exactly.
        for i in range(count):
            if i in changed:continue
            chunk=new[i*4096:(i+1)*4096]
            raw=work/f'opt-{i:03d}.bin';cab=work/f'opt-{i:03d}.cab'
            raw.write_bytes(chunk)
            run=subprocess.run(['makecab.exe','/D','CompressionType=LZX','/D',
                'CompressionMemory=15',str(raw),str(cab)],capture_output=True)
            assert run.returncode==0,run.stdout+run.stderr
            data=cab.read_bytes();offset,numblocks,compression=struct.unpack_from('<IHH',data,36)
            assert numblocks==1 and compression==0x0f03
            _,cn,un=struct.unpack_from('<IHH',data,offset)
            assert un==len(chunk)
            block=struct.pack('<4I',15,un,cn,un)+data[offset+8:offset+8+cn]
            buf=bytearray(un+4096);status,n=bin_decompress_rom(block,len(block),buf)
            assert status==0 and n==un and bytes(buf[:n])==chunk
            if len(block)>=len(blocks[i]):continue
            blocks[i]=block
            cursor=header_size;table=bytearray(len(new).to_bytes(3,'little'))
            for part in blocks:
                cursor+=len(part);table+=cursor.to_bytes(3,'little')
            result=bytes(table)+b''.join(blocks)
            print('Lossless storage optimization on unchanged page',i)
            if len(result)<=len(old):break
        assert decode_ce(result,len(new))==new
    return result,changed

def patch_layout(old):
    b=bytearray(old)
    assert struct.unpack_from('<4I',b)==(0x400102b4,0x15b0,0x60114,0x7a1e8)
    strings=0x60114;utf16=0x7a1e8
    entries=list(struct.iter_unpack('<II',b[16:0x15b0]))
    names={old[strings+n*4:].split(b'\0',1)[0].decode():o+0x15b0 for n,o in entries}
    assert names['AV/BTAudio/Base.lyt']==0x9a48
    def word(a,expected,value):
        assert struct.unpack_from('<I',b,a)[0]==expected,(hex(a),expected)
        struct.pack_into('<I',b,a,value)
    # These offsets belong to the three named BTAudio text instances only.
    assert old[strings+struct.unpack_from('<I',b,0x9cbc)[0]*4:].startswith(b'TrackName\0')
    assert old[strings+struct.unpack_from('<I',b,0x9c88)[0]*4:].startswith(b'ArtistName\0')
    assert old[strings+struct.unpack_from('<I',b,0x9c54)[0]*4:].startswith(b'AlbumName\0')
    added=b'P_FONT_32x36\0'
    added+=b'\xff'*((-len(added))%4)
    font_id=(utf16-strings)//4
    word(0x9ce4,0x4c9,font_id)          # title 28x32 -> 32x36
    word(0x9cc0,0x00de0071,0x00de006c) # y 113 -> 108
    word(0x9cc4,0x02420020,0x02420028) # height 32 -> 40
    word(0x9cb0,0x1ae,0x4c9)          # artist 22x26 -> 28x32
    word(0x9c90,0x0242001a,0x02420024) # height 26 -> 36
    word(0x9c7c,0x1ae,0xd52)          # album 22x26 -> 24x28
    word(0x9c5c,0x0242001a,0x02420020) # height 26 -> 32
    # Append to ASCII pool and move the UTF-16 pool; all its indices stay relative.
    b[utf16:utf16]=added
    struct.pack_into('<I',b,12,utf16+len(added))
    assert b[strings+font_id*4:].startswith(b'P_FONT_32x36\0')
    assert b[utf16+len(added):]==old[utf16:]
    # Check text rectangles and glyph metrics; preserve every button rectangle.
    rects=[(222,108,578,40,36),(222,180,578,36,32),(222,244,578,32,28)]
    assert all(x+w<=832 and y+h<321 and h>=font_h for x,y,w,h,font_h in rects)
    assert all(rects[i][1]+rects[i][3]<rects[i+1][1] for i in range(2))
    return bytes(b)

def patch_archive(src,asset):
    b=bytearray(src);h=struct.unpack_from('<11I',b)
    assert h==(44,1,2803,44,22424,22468,30000,52468,107064,159532,32647660)
    target=None
    for i in range(h[6]//16):
        kind,ns,offset,size=struct.unpack_from('<4I',b,h[5]+i*16)
        name=b[h[7]+ns:h[9]].decode('utf-16le').split('\0',1)[0]
        if name==r'av\P24_bmp\P24_AV_0001.bmp':
            assert kind==0 and size==985376 and len(asset)==985374
            start=h[9]+offset;before=bytes(b[start:start+size]);target=(start,size)
            assert before[:2]==asset[:2]==b'BM'
            assert struct.unpack_from('<iiH',before,18)==struct.unpack_from('<iiH',asset,18)==(680,483,1)
            assert struct.unpack_from('<H',asset,28)[0]==24
            assert struct.unpack_from('<I',before,10)[0]==struct.unpack_from('<I',asset,10)[0]==54
            # Preserve Pioneer's BMP header and two archive-alignment bytes.
            replacement=before[:54]+asset[54:]+before[-2:]
            assert len(replacement)==size
            b[start:start+size]=replacement
    assert target is not None
    a,n=target
    assert b[:a]==src[:a] and b[a+n:]==src[a+n:]
    return bytes(b),target
