#!/usr/bin/env python3
"""Pioneer AVIC (EU130 / 2013) update-package tool.

Formats (all little-endian, magic A5 5A 5A A5):

.PRG  (PLATFORM/EU130PLT.PRG)
  0x000 magic
  0x004 payload size  (file size - 0x200)
  0x008 payload sum   (sum of payload as u32 words, mod 2^32)
  0x00C version       (0x01060000 = 1.06)
  0x010 u32 1, 0x014 u32 0
  0x018 name   (ASCII, e.g. "EU130PLT.PRG")
  0x028 build date (ASCII, "2013/12/20_16:03")
  0x048 load address, 0x04C entry point (SH-4, 0x884A1000 / 0x884A1004)
  0x050 u32 4, then 0xFF padding
  0x1FC header sum    (sum of u32 words over 0x000-0x1FB)
  0x200 payload: raw Windows CE ROM image ("ECEC" at payload+0x40)

.VER  (EU130APL.VER / EU130PLT.VER) - file manifest
  0x000 magic, 0x004 total file size, 0x008 version, 0x00C 1, 0x010 0
  0x014 u32 0x2C
  0x018 20 bytes: copy of PRG header 0x004-0x017 (PLT only, zeros for APL)
  0x02C number of files
  0x030 groups, repeated:
          u32 n_components, n_components x 64-byte UTF-16 dir names,
          u32 n_files, n_files x { 56-byte UTF-16 name, u32 size, u32 CRC32 }
  end-8 magic, end-4 CRC32 of everything before it
"""
import argparse
import os
import struct
import sys
import zlib

MAGIC = 0xA55A5AA5
PRG_HDR = 0x200


def sum32(data):
    n = len(data) // 4
    return sum(struct.unpack_from('<%dI' % n, data)) & 0xFFFFFFFF


def crc32_file(path):
    c = 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                return c
            c = zlib.crc32(b, c)


def utf16_field(s, size):
    raw = s.encode('utf-16-le')
    if len(raw) > size - 2:
        raise ValueError('name too long: %r' % s)
    return raw.ljust(size, b'\0')


def read_utf16(buf, off, size):
    return buf[off:off + size].decode('utf-16-le').split('\0', 1)[0]


# ---------------------------------------------------------------- PRG

def parse_prg_header(h):
    magic, size, psum, ver, one, zero = struct.unpack_from('<6I', h, 0)
    return {
        'magic': magic, 'payload_size': size, 'payload_sum': psum,
        'version': ver, 'f10': one, 'f14': zero,
        'name': h[0x18:0x28].split(b'\0', 1)[0].decode('ascii'),
        'date': h[0x28:0x48].split(b'\0', 1)[0].decode('ascii'),
        'load': struct.unpack_from('<I', h, 0x48)[0],
        'entry': struct.unpack_from('<I', h, 0x4C)[0],
        'hdr_sum': struct.unpack_from('<I', h, 0x1FC)[0],
    }


def check_prg(path):
    with open(path, 'rb') as f:
        d = f.read()
    h = parse_prg_header(d)
    ok = True
    ok &= report('PRG magic', h['magic'] == MAGIC)
    ok &= report('PRG payload size', h['payload_size'] == len(d) - PRG_HDR,
                 '%#x' % h['payload_size'])
    ok &= report('PRG payload sum', h['payload_sum'] == sum32(d[PRG_HDR:]),
                 '%#010x' % h['payload_sum'])
    ok &= report('PRG header sum', h['hdr_sum'] == sum32(d[:0x1FC]),
                 '%#010x' % h['hdr_sum'])
    print('    %s  v%x  built %s  load %#x  entry %#x' %
          (h['name'], h['version'], h['date'], h['load'], h['entry']))
    return ok


def fix_prg(path, out):
    """Recompute size and both sums of a (possibly patched) PRG."""
    with open(path, 'rb') as f:
        d = bytearray(f.read())
    struct.pack_into('<I', d, 4, len(d) - PRG_HDR)
    struct.pack_into('<I', d, 8, sum32(d[PRG_HDR:]))
    struct.pack_into('<I', d, 0x1FC, sum32(d[:0x1FC]))
    with open(out, 'wb') as f:
        f.write(d)


# ---------------------------------------------------------------- VER

def parse_ver(buf):
    magic, total, ver, f0c, f10, f14 = struct.unpack_from('<6I', buf, 0)
    prg_info = buf[0x18:0x2C]
    count = struct.unpack_from('<I', buf, 0x2C)[0]
    off = 0x30
    groups = []
    end = len(buf) - 8
    while off < end:
        ncomp = struct.unpack_from('<I', buf, off)[0]
        off += 4
        comps = []
        for _ in range(ncomp):
            comps.append(read_utf16(buf, off, 64))
            off += 64
        nfiles = struct.unpack_from('<I', buf, off)[0]
        off += 4
        files = []
        for _ in range(nfiles):
            name = read_utf16(buf, off, 56)
            size, crc = struct.unpack_from('<II', buf, off + 56)
            files.append((name, size, crc))
            off += 64
        groups.append((comps, files))
    tmagic, tcrc = struct.unpack_from('<II', buf, end)
    return {'magic': magic, 'total': total, 'version': ver, 'f0c': f0c,
            'f10': f10, 'f14': f14, 'prg_info': prg_info, 'count': count,
            'groups': groups, 'tmagic': tmagic, 'tcrc': tcrc}


def build_ver(m, root):
    """Build a manifest with the same layout as m, sizes/CRCs read from root."""
    body = bytearray()
    count = 0
    prg_info = m['prg_info']
    for comps, files in m['groups']:
        body += struct.pack('<I', len(comps))
        for c in comps:
            body += utf16_field(c, 64)
        body += struct.pack('<I', len(files))
        for name, _, _ in files:
            p = os.path.join(root, *comps, name)
            size = os.path.getsize(p)
            body += utf16_field(name, 56) + struct.pack('<II', size, crc32_file(p))
            count += 1
            if name.upper().endswith('.PRG') and any(prg_info):
                with open(p, 'rb') as f:
                    prg_info = f.read(0x18)[4:0x18]
    total = 0x30 + len(body) + 8
    hdr = struct.pack('<6I', MAGIC, total, m['version'], m['f0c'], m['f10'],
                      m['f14']) + prg_info + struct.pack('<I', count)
    out = hdr + bytes(body) + struct.pack('<I', MAGIC)
    return out + struct.pack('<I', zlib.crc32(out))


def check_ver(path, root):
    with open(path, 'rb') as f:
        buf = f.read()
    m = parse_ver(buf)
    ok = True
    ok &= report('%s magic/size' % os.path.basename(path),
                 m['magic'] == MAGIC and m['total'] == len(buf) and m['tmagic'] == MAGIC)
    ok &= report('%s trailer CRC32' % os.path.basename(path),
                 m['tcrc'] == zlib.crc32(buf[:-4]), '%#010x' % m['tcrc'])
    n = 0
    for comps, files in m['groups']:
        for name, size, crc in files:
            n += 1
            p = os.path.join(root, *comps, name)
            rel = '/'.join(comps + [name])
            if not os.path.exists(p):
                ok &= report(rel, False, 'missing')
                continue
            asz, acrc = os.path.getsize(p), crc32_file(p)
            good = asz == size and acrc == crc
            ok &= good
            if not good or VERBOSE:
                report(rel, good, 'size %d/%d crc %#010x/%#010x' % (asz, size, acrc, crc))
    ok &= report('%s file count' % os.path.basename(path), n == m['count'], str(n))
    return ok


# ---------------------------------------------------------------- CLI

VERBOSE = False


def report(what, good, extra=''):
    print('  [%s] %s %s' % ('OK ' if good else 'BAD', what, extra))
    return good


def cmd_verify(a):
    root = a.root
    ok = True
    for ver in sorted(f for f in os.listdir(root) if f.upper().endswith('.VER')):
        ok &= check_ver(os.path.join(root, ver), root)
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.upper().endswith('.PRG'):
                ok &= check_prg(os.path.join(dirpath, n))
    print('ALL OK' if ok else 'PROBLEMS FOUND')
    return 0 if ok else 1


def cmd_rebuild_ver(a):
    with open(a.ver, 'rb') as f:
        orig = f.read()
    new = build_ver(parse_ver(orig), a.root)
    with open(a.out, 'wb') as f:
        f.write(new)
    print('wrote %s (%d bytes), identical to input: %s' % (a.out, len(new), new == orig))


def cmd_fix_prg(a):
    fix_prg(a.prg, a.out)
    print('wrote', a.out)


def cmd_info(a):
    with open(a.ver, 'rb') as f:
        m = parse_ver(f.read())
    print('version %#x, %d files' % (m['version'], m['count']))
    for comps, files in m['groups']:
        for name, size, crc in files:
            print('  %10d  %08x  %s' % (size, crc, '/'.join(comps + [name])))


def main():
    global VERBOSE
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('-v', action='store_true', help='verbose')
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('verify', help='check every checksum in a package folder')
    p.add_argument('root')
    p.set_defaults(fn=cmd_verify)
    p = sp.add_parser('info', help='list a .VER manifest')
    p.add_argument('ver')
    p.set_defaults(fn=cmd_info)
    p = sp.add_parser('rebuild-ver', help='regenerate a .VER from the files on disk')
    p.add_argument('ver')
    p.add_argument('root')
    p.add_argument('out')
    p.set_defaults(fn=cmd_rebuild_ver)
    p = sp.add_parser('fix-prg', help='recompute size and sums of a .PRG')
    p.add_argument('prg')
    p.add_argument('out')
    p.set_defaults(fn=cmd_fix_prg)
    a = ap.parse_args()
    VERBOSE = a.v
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
