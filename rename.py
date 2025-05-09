# make_rename.py
import re, os, unicodedata, csv, pathlib
DIR = pathlib.Path('.')       # 현재 폴더
out_sh  = DIR/'rename_commands.sh'
out_csv = DIR/'rename_mapping.csv'
pat = re.compile(r'\[(\d+호선)-(.+?)\(\d+\)]-\[\d+호선 (.+?) (\d{3})]')  # 패턴 ①
pat2= re.compile(r'^(\d+)[\._\- ]+(.+?)\.(jpg|JPG)$')                   # 패턴 ② (1.응암, 124 청량리 처럼)

rows, sh_lines = [], ['#!/usr/bin/env bash\nset -eu\n']
for f in DIR.iterdir():
    if f.is_file():
        name = unicodedata.normalize('NFC', f.name)   # 맥·리눅스 unicode 차이 방지
        new = None
        m = pat.search(name)
        if m:                     # [3호선-충무로(3)]-[3호선 충무로 331]...
            code, stn = m.group(4), m.group(3)
            ext  = f.suffix
            new  = f'{code}({stn}).{ext.lstrip(".")}'
        else:
            m2 = pat2.match(name) # 1.-응암.jpg  / 124 청량리.jpg
            if m2:
                idx, stn, ext = m2.groups()
                # 앞의 인덱스가 실제 역코드가 아닌 경우가 있으니 그대로 두고 패스
                # 나중에 수동으로 고칠 수 있게 빈 new 로 둠
        if new:
            rows.append([name, new])
            sh_lines.append(f'mv -- "{name}" "{new}"')
out_csv.write_text('\n'.join(','.join(r) for r in rows), encoding='utf-8')
out_sh .write_text('\n'.join(sh_lines),              encoding='utf-8')
print(f'✓ {len(rows)}개 변환 규칙 생성 → {out_sh}')