#!/bin/zsh
setopt nullglob

cd 입체구조도 || exit 1

# 상가위치도에서 기준 이름 목록 추출
store_dir="./상가위치도"
store_files=("${store_dir}"/*)

for file in *(.jpg|.JPG|.jpeg|.JPEG|.png|.PNG); do
  matched=""
  for store_path in "${store_files[@]}"; do
    store_file="${store_path##*/}"             # 예: 150(서울역).jpg
    station=$(echo "$store_file" | sed -E 's/^[0-9]+[(](.*)[)].*$/\1/')  # 예: 서울역

    if [[ "$file" == *"$station"* ]]; then
      matched="$store_file"
      break
    fi
  done

  if [[ -n "$matched" && "$file" != "$matched" ]]; then
    echo "✅ $file → $matched"
    mv "$file" "$matched"
  fi
done