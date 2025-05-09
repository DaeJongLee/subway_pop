import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import matplotlib
import os
import glob  # at the top with other imports
from PIL import Image
matplotlib.rc('font', family='AppleGothic')  # macOS용 한글 폰트
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 깨짐 방지

# 데이터 로드
@st.cache_data
def load_data():
    df = pd.read_csv("data.csv")
    df['수송일자'] = pd.to_datetime(df['수송일자'])
    df['요일'] = df['수송일자'].dt.day_name(locale='ko_KR')  # 'Monday' → '월요일' 등
    df['총유동인구'] = df.loc[:, df.columns.str.contains("시간대")].sum(axis=1)
    return df

df = load_data()

# 시간대 열 자동 추출
time_columns = [col for col in df.columns if '시간대' in col]

# 사이드바 필터
st.sidebar.title("📊 지하철 유동인구 분석")
역명_list = st.sidebar.multiselect("역 선택 (다중 가능)", sorted(df['역명'].unique()), default=[df['역명'].unique()[0]])
구분 = st.sidebar.radio("승하차 구분", ['전체', '승차', '하차'])
날짜범위 = st.sidebar.date_input("날짜 범위 선택", 
                            value=(pd.to_datetime("2023-01-01"), pd.to_datetime("2023-12-30")),
                            min_value=pd.to_datetime("2023-01-01"),
                            max_value=pd.to_datetime("2023-12-30"))

# 필터링
start_date, end_date = map(pd.to_datetime, 날짜범위)
filtered = df[(df['역명'].isin(역명_list)) & 
              (df['수송일자'] >= start_date) & (df['수송일자'] <= end_date)]
if 구분 != '전체':
    filtered = filtered[filtered['승하차구분'] == 구분]

# Tabs
tab1, tab2 = st.tabs(["📊 유동인구 분석", "🏪 상가 위치 보기"])

with tab1:
    st.title(f"📍 {', '.join(역명_list)}역 유동인구 분석")
    st.write(f"### ⏰ {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} {구분} 시간대별 인원")

    col_graph, col_stats = st.columns([2, 1])

    if not filtered.empty:
        with col_graph:
            fig, ax = plt.subplots(figsize=(12, 4))
            for 역 in 역명_list:
                row = filtered[filtered['역명'] == 역]
                if not row.empty:
                    # 평균값으로 시간대별 인원 계산
                    values = row[time_columns].mean()
                    ax.plot(range(len(time_columns)), values, marker='o', label=역)
            ax.set_xticks(range(len(time_columns)))
            ax.set_xticklabels(time_columns, rotation=45)
            ax.set_ylabel("인원수")
            ax.legend()
            st.pyplot(fig)

            # 요일별 평균 분석 (Altair 사용)
            st.write("### 📅 요일별 평균 유동인구 (Altair)")
            weekday_order = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
            plot_data = []

            for 역 in 역명_list:
                sub = df[df['역명'] == 역]
                if 구분 != '전체':
                    sub = sub[sub['승하차구분'] == 구분]
                grouped = sub.groupby('요일')['총유동인구'].mean().reindex(weekday_order).reset_index()
                grouped['역명'] = 역
                plot_data.append(grouped)

            chart_df = pd.concat(plot_data)

            chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X('요일:N', sort=weekday_order, title='요일'),
                y=alt.Y('총유동인구:Q', title='유동인구 수'),
                color='역명:N',
                tooltip=['역명', '요일', '총유동인구']
            ).properties(
                width=600,
                height=400,
                title='요일별 유동인구 비교 (Altair)'
            )

            st.altair_chart(chart, use_container_width=True)

            # 총 유동인구 월별 추이 (역별 분리 Altair)
            st.write("### 📈 월별 총 유동인구 추이 (역별 비교)")

            monthly_df = df[(df['역명'].isin(역명_list))].copy()
            if 구분 != '전체':
                monthly_df = monthly_df[monthly_df['승하차구분'] == 구분]

            monthly_df['월'] = monthly_df['수송일자'].dt.to_period('M').astype(str)
            monthly_grouped = monthly_df.groupby(['월', '역명'])['총유동인구'].sum().reset_index()

            monthly_chart = alt.Chart(monthly_grouped).mark_line(point=True).encode(
                x=alt.X('월:N', title='월'),
                y=alt.Y('총유동인구:Q', title='유동인구 수'),
                color=alt.Color('역명:N'),
                tooltip=['월', '역명', '총유동인구']
            ).properties(
                width=700,
                height=400
            )

            st.altair_chart(monthly_chart, use_container_width=True)
        with col_stats:
            st.subheader("📌 통계 요약 (표 형식)")

            rows = []
            weekday = ['월요일', '화요일', '수요일', '목요일', '금요일']

            for 역 in 역명_list:
                역_filtered = filtered[filtered['역명'] == 역]
                노선들 = df[df['역명'] == 역]['호선'].unique()
                total_flow = 역_filtered['총유동인구'].sum()

                daily_by_day = 역_filtered.groupby('요일')['총유동인구'].mean().round(1)
                평일 = daily_by_day[daily_by_day.index.isin(weekday)].mean() if any(daily_by_day.index.isin(weekday)) else 0
                토요일 = daily_by_day.get('토요일', 0)
                일요일 = daily_by_day.get('일요일', 0)

                rows.append({
                    "역명": 역,
                    "노선": ", ".join(노선들),
                    "전체 유동인구": f"{int(total_flow):,}",
                    "평일 평균": f"{int(평일):,}",
                    "토요일 평균": f"{int(토요일):,}",
                    "일요일 평균": f"{int(일요일):,}",
                })

            summary_df = pd.DataFrame(rows).set_index("역명").T
            st.dataframe(summary_df)

            if len(역명_list) > 1:
                st.subheader("🏆 유동인구 순위")

                total_rank = filtered.groupby('역명')['총유동인구'].sum().sort_values(ascending=False)
                st.write("**전체 기간 유동인구 순위**")
                st.table(total_rank.rename("명"))

                st.write("**요일별 유동인구 순위**")
                day_rank = filtered.groupby(['요일', '역명'])['총유동인구'].sum().unstack().fillna(0)
                st.dataframe(day_rank.style.format("{:,.0f}"))
    else:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")

# 상가 위치 보기 탭
with tab2:
    st.subheader("🏪 선택한 역의 상가 및 입체 구조도")
    for 역 in 역명_list:
        code_rows = df[df['역명'] == 역]
        if code_rows.empty:
            continue
        codes = code_rows['역번호'].unique()
        for code in codes:
            # 파일명 통일 규칙 → "코드(역명).jpg"
            filename = f"{int(code)}({역}).jpg"
            shop_path   = os.path.join("./상가위치도", filename)
            struct_path = os.path.join("./입체구조도", filename)

            col1, col2 = st.columns(2)

            # ───── 상가 위치도 ─────
            with col1:
                if os.path.exists(shop_path):
                    st.image(Image.open(shop_path),
                             caption=f"[상가위치도] {역} ({code})",
                             use_container_width=True)
                else:
                    # 폴더 구조가 바뀌었을 수도 있으니 역명 기준으로 보조 검색
                    alt_shop = glob.glob(f"상가위치도/**/{역}*.jp*g", recursive=True)
                    if alt_shop:
                        st.image(alt_shop[0],
                                 caption=f"[상가위치도] {os.path.basename(alt_shop[0])}",
                                 use_container_width=True)
                    else:
                        st.warning(f"{역}의 상가 이미지({code})가 없습니다.")

            # ───── 입체 구조도 ─────
            with col2:
                if os.path.exists(struct_path):
                    st.image(Image.open(struct_path),
                             caption=f"[입체구조도] {역} ({code})",
                             use_container_width=True)
                else:
                    # 역명으로 백업 검색 (폴더/확장자 다양성 대비)
                    struct_images = glob.glob(f"입체구조도/**/{역}*.jp*g", recursive=True)
                    if struct_images:
                        st.image(struct_images[0],
                                 caption=f"[입체구조도] {os.path.basename(struct_images[0])}",
                                 use_container_width=True)
                    else:
                        st.info(f"{역}의 입체구조도 이미지가 없습니다.")