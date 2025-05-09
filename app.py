import streamlit as st
st.set_page_config(layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import matplotlib
import os
import glob
from PIL import Image

# ────────────────────────────────────────────────────────────
# 기본 설정 (폰트‧마이너스 깨짐 방지)
# ────────────────────────────────────────────────────────────
matplotlib.rc('font', family='AppleGothic')  # macOS 한글 폰트
plt.rcParams['axes.unicode_minus'] = False

# ────────────────────────────────────────────────────────────
# 데이터 로더
# ────────────────────────────────────────────────────────────
@st.cache_data
def load_pop_data():
    """유동인구 CSV 로드 & 전처리"""
    df = pd.read_csv("data.csv")
    df['수송일자'] = pd.to_datetime(df['수송일자'])

    # locale 설치가 안 된 환경을 위해 weekday 숫자 → 한글 매핑
    weekday_map = {
        0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일',
        4: '금요일', 5: '토요일', 6: '일요일'
    }
    df['요일'] = df['수송일자'].dt.weekday.map(weekday_map)

    df['총유동인구'] = df.loc[:, df.columns.str.contains("시간대")].sum(axis=1)
    return df

@st.cache_data
def load_store_data():
    """역구내 상가 현황 CSV 로드 (연도, 연번 열 제거)"""
    store = pd.read_csv("store.csv")
    # 역번호(정수) 추출 → 상가번호 앞자리
    store["역번호"] = store["상가번호"].str.split("-").str[0].astype(int)

    # 역명에 붙은 "(1)" 같은 괄호 제거
    store["역명"] = store["역명"].str.replace(r"\s*\([^)]*\)", "", regex=True)

    store = store.drop(columns=['연도', '연번'], errors='ignore')
    return store

pop_df   = load_pop_data()
store_df = load_store_data()

# 시간대 열 자동 추출
TIME_COLS = [c for c in pop_df.columns if '시간대' in c]

# ────────────────────────────────────────────────────────────
# 사이드바 필터링 UI
# ────────────────────────────────────────────────────────────
st.sidebar.title("📊 지하철 유동인구 분석")
역명_list = st.sidebar.multiselect("역 선택 (다중 가능)",
                            sorted(pop_df['역명'].unique()),
                            default=[pop_df['역명'].unique()[0]])
구분 = st.sidebar.radio("승하차 구분", ['전체', '승차', '하차'])
날짜범위 = st.sidebar.date_input("날짜 범위 선택",
                            value=(pd.to_datetime("2023-01-01"), pd.to_datetime("2023-12-30")),
                            min_value=pd.to_datetime("2023-01-01"),
                            max_value=pd.to_datetime("2023-12-30"))
start_date, end_date = map(pd.to_datetime, 날짜범위)

# ────────────────────────────────────────────────────────────
# 데이터 필터링
# ────────────────────────────────────────────────────────────
filtered = pop_df[(pop_df['역명'].isin(역명_list)) &
                 (pop_df['수송일자'] >= start_date) & (pop_df['수송일자'] <= end_date)]
if 구분 != '전체':
    filtered = filtered[filtered['승하차구분'] == 구분]

# ────────────────────────────────────────────────────────────
# 탭 레이아웃
# ────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 유동인구 분석", "🏪 상가 위치 보기"])

# ----------------------------------------------------------
# 📊 TAB 1 : 유동인구 분석
# ----------------------------------------------------------
with tab1:
    st.title(f"📍 {', '.join(역명_list)}역 유동인구 분석")
    st.write(f"### ⏰ {start_date.date()} ~ {end_date.date()} {구분} 시간대별 인원")

    col_graph, col_stats = st.columns([2, 1])

    if not filtered.empty:
        # ── 라인 차트 ──
        with col_graph:
            fig, ax = plt.subplots(figsize=(12, 4))
            for 역 in 역명_list:
                rows = filtered[filtered['역명'] == 역]
                if rows.empty:
                    continue
                ax.plot(range(len(TIME_COLS)), rows[TIME_COLS].mean(), marker='o', label=역)
            ax.set_xticks(range(len(TIME_COLS)))
            ax.set_xticklabels(TIME_COLS, rotation=45)
            ax.set_ylabel("인원수")
            ax.legend()
            st.pyplot(fig)

            # ── Altair 요일별 평균 ──
            st.write("### 📅 요일별 평균 유동인구 (Altair)")
            weekday_order = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일']
            plot_df_list = []
            for 역 in 역명_list:
                sub = pop_df[pop_df['역명'] == 역]
                if 구분 != '전체':
                    sub = sub[sub['승하차구분'] == 구분]
                grouped = (sub.groupby('요일')['총유동인구']
                              .mean()
                              .reindex(weekday_order)
                              .reset_index())
                grouped['역명'] = 역
                plot_df_list.append(grouped)
            chart_df = pd.concat(plot_df_list)
            chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X('요일:N', sort=weekday_order),
                y='총유동인구:Q',
                color='역명:N',
                tooltip=['역명','요일','총유동인구']
            ).properties(width=600, height=400)
            st.altair_chart(chart, use_container_width=True)

            # ── 월별 추이 ──
            st.write("### 📈 월별 총 유동인구 추이 (역별 비교)")
            mdf = pop_df[pop_df['역명'].isin(역명_list)].copy()
            if 구분 != '전체':
                mdf = mdf[mdf['승하차구분'] == 구분]
            mdf['월'] = mdf['수송일자'].dt.to_period('M').astype(str)
            m_grouped = mdf.groupby(['월','역명'])['총유동인구'].sum().reset_index()
            m_chart = alt.Chart(m_grouped).mark_line(point=True).encode(
                x='월:N', y='총유동인구:Q', color='역명:N', tooltip=['월','역명','총유동인구']
            ).properties(width=700, height=400)
            st.altair_chart(m_chart, use_container_width=True)

        # ── 통계 요약 ──
        with col_stats:
            st.subheader("📌 통계 요약")
            rows = []
            weekday = ['월요일','화요일','수요일','목요일','금요일']
            for 역 in 역명_list:
                sub = filtered[filtered['역명'] == 역]
                노선 = pop_df[pop_df['역명'] == 역]['호선'].unique()
                total = int(sub['총유동인구'].sum())
                by_day = sub.groupby('요일')['총유동인구'].mean()
                평일 = by_day[by_day.index.isin(weekday)].mean() if not by_day.empty else 0
                토 = by_day.get('토요일',0)
                일 = by_day.get('일요일',0)
                rows.append({
                    '역명':역,
                    '노선':", ".join(노선),
                    '전체 유동인구':f"{total:,}",
                    '평일 평균':f"{int(평일):,}",
                    '토요일 평균':f"{int(토):,}",
                    '일요일 평균':f"{int(일):,}"
                })
            stat_df = pd.DataFrame(rows).set_index('역명').T
            st.dataframe(stat_df)

            # ── 유동인구 순위 ──
            if len(역명_list) > 1:
                st.subheader("🏆 유동인구 순위")
                total_rank = filtered.groupby('역명')['총유동인구'].sum().sort_values(ascending=False)
                st.table(total_rank.rename("명"))

    else:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")

# ----------------------------------------------------------
# 🏪 TAB 2 : 상가 위치 & 입체 구조도 + 임대 데이터
# ----------------------------------------------------------
with tab2:
    st.subheader("🏪 선택한 역의 상가 · 입체 구조도 · 임대 현황")

    # ────────────────────────────────────────────────────────
    # 선택한 모든 역을 순회 (다중 노선이라도 전부 처리)
    # ────────────────────────────────────────────────────────
    for 역 in 역명_list:
        # 한 역이 여러 노선에 걸쳐 있을 수 있으므로 → 모든 코드 수집
        codes = (pop_df[pop_df['역명'] == 역]['역번호']
                    .dropna()
                    .unique())

        if len(codes) == 0:
            continue

        st.markdown(f"## 🚉 {역}")

        for code in codes:
            code = int(code)          # numpy 타입 → int 로 변환
            st.markdown(f"### 노선 코드: {code}")

            img_col1, img_col2 = st.columns(2)

            # ── 상가 위치도 ────────────────────────────────
            with img_col1:
                # 역명 먼저 검색 → 없으면 코드로 백업
                shop_matches = glob.glob(
                    f"상가위치도/**/{역}*.jp*g", recursive=True)

                if not shop_matches:
                    shop_matches = glob.glob(
                        f"상가위치도/**/{code}(*.jp*g", recursive=True)

                if shop_matches:
                    for p in shop_matches:
                        st.image(p, caption=os.path.basename(p),
                                 use_container_width=True)
                else:
                    st.info("상가 위치도 이미지 없음")

            # ── 입체 구조도 ────────────────────────────────
            with img_col2:
                # 역명 먼저 검색 → 없으면 코드로 백업
                struct_matches = glob.glob(
                    f"입체구조도/**/{역}*.jp*g", recursive=True)

                if not struct_matches:
                    struct_matches = glob.glob(
                        f"입체구조도/**/{code}(*.jp*g", recursive=True)

                if struct_matches:
                    for p in struct_matches:
                        st.image(p, caption=os.path.basename(p),
                                 use_container_width=True)
                else:
                    st.info("입체 구조도 이미지 없음")

            # ── 임대 현황 표  ──────────────────────────────
            lease = store_df[store_df["역번호"] == code]
            if lease.empty:
                st.info("임대 현황 데이터가 없습니다.")
            else:
                show_cols = ['상가유형', '호선', '상가번호', '면적(제곱미터)',
                             '영업업종', '계약시작일자', '계약종료일자',
                             '월임대료', '사업진행단계']
                st.dataframe(lease[show_cols].reset_index(drop=True))
