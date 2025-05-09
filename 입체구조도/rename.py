import re, os, unicodedata, csv, pathlib
DIR = pathlib.Path('.')                 # 현재 디렉터리
out_sh  = DIR/'rename_commands.sh'
out_csv = DIR/'rename_mapping.csv'

# 패턴 ①  ―  [3호선-충무로(3)]-[3호선 충무로 331]역이용안내도.jpg
pat1 = re.compile(r'\[(\d+)호선-(.+?)\(\d+\)]-\[\d+호선 (.+?) (\d{3})]')
# 패턴 ②  ―  1.-응암.jpg   / 124 청량리.jpg
pat2 = re.compile(r'^(\d+)[\.\-_ ]+(.*?)\.(jpg|JPG)$')

rows, sh_lines = [], ['#!/usr/bin/env bash\nset -eu\n']
for f in DIR.iterdir():
    if not f.is_file():                # 디렉터리 건너뜀
        continue
    name = unicodedata.normalize('NFC', f.name)     # 한글 조합 방식 통일
    new_name = None
    if (m:=pat1.search(name)):
        new_name = f'{m.group(4)}({m.group(3)}).{f.suffix.lstrip(".")}'
    elif (m:=pat2.match(name)):
        # 패턴②는 코드가 실제 역코드가 아닌 경우도 많으니 “보류” – 필요 시 직접 고치세요
        pass
    if new_name:
        rows.append([name, new_name])
        sh_lines.append(f'mv -- \"{name}\" \"{new_name}\"')

# 결과물 저장
out_csv.write_text('\n'.join(','.join(r) for r in rows), encoding='utf-8')
out_sh .write_text('\n'.join(sh_lines),              encoding='utf-8')
print(f'✓ {len(rows)} 개의 rename 규칙 생성 → {out_sh}')
