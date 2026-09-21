from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# 1. 스트림릿 페이지 기본 설정
st.set_page_config(
    page_title="어제 기준 박스오피스 순위", page_icon="🎬", layout="wide"
)

st.title("🎬 어제의 영화 박스오피스 TOP 10")
st.markdown(
    "영화진흥위원회(KOBIS) 공식 API를 활용하여 한국 시간 기준 어제의 실시간"
    " 박스오피스 순위를 제공합니다."
)

# 2. 한국 시간(KST, UTC+9) 기준으로 '어제' 날짜 계산하기
# (스트림릿 클라우드 서버는 기본적으로 UTC 기준이므로 시간대를 맞추어야 합니다)
kst = timezone(timedelta(hours=9))
yesterday = datetime.now(kst) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

# 화면에 보여줄 날짜 포맷 (예: 2026년 06월 07일)
display_date = f"{target_dt[:4]}년 {target_dt[4:6]}월 {target_dt[6:]}일"
st.info(f"📅 조회 기준일: **{display_date}** (한국 시간 기준 어제)")


# 3. KOBIS API 데이터 호출 함수
@st.cache_data(ttl=3600)  # 1시간 동안 데이터를 캐시하여 불필요한 API 호출 방지
def fetch_box_office_data(date_str):
  # 비밀 금고(secrets)에서 KOBIS_KEY 불러오기
  try:
    api_key = st.secrets["KOBIS_KEY"]
  except Exception:
    return None, (
        "Secret 설정 오류: Streamlit Cloud의 Settings > Secrets에 'KOBIS_KEY'"
        " 가 등록되어 있는지 확인해주세요."
    )

  # 공식 문서에 안내된 요청 주소
  url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
  params = {"key": api_key, "targetDt": date_str}

  try:
    response = requests.get(url, params=params)
    data = response.json()

    # 인증키가 틀려도 200 코드를 주며 faultInfo 상자가 오는 경우 처리
    if "faultInfo" in data:
      return (
          None,
          f"API 인증 오류 (faultInfo): {data['faultInfo']}\n시크릿에 입력된"
          " 인증키(KOBIS_KEY)가 올바른지 확인해주세요.",
      )

    if "boxOfficeResult" not in data:
      return (
          None,
          "API 응답 구조가 올바르지 않습니다. 네트워크 상태나 API 서버를"
          " 확인해주세요.",
      )

    box_office_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

    if not box_office_list:
      return (
          None,
          "해당 날짜에 집계된 영화 목록이 없습니다. (아직 집계 전이거나 휴일일"
          " 수 있습니다.)",
      )

    return box_office_list, None

  except Exception as e:
    return (
        None,
        f"요청 중 오류가 발생했습니다: {e}\n인터넷 연결 상태나 API 주소를"
        " 확인해주세요.",
    )


# 4. 데이터 불러오기 실행
raw_data, error_message = fetch_box_office_data(target_dt)

# 5. 요청이 실패하거나, 오류 상자가 오거나, 영화 목록이 비었을 때 안내문 출력
if error_message:
  st.error(
      "⚠️ **데이터를 불러오지 못했습니다.**\n\n확인해야 할 사항:\n1. Streamlit"
      " Cloud의 **Secrets** 메뉴에 `KOBIS_KEY`가 올바르게 등록되어 있는지"
      " 확인해주세요.\n2. KOBIS API 인증키가 정상 발급 및 활성화 상태인지"
      " 확인해주세요.\n3. 오늘 날짜는 아직 박스오피스가 집계되지 않았을 수"
      " 있으므로 '어제' 기준일이 올바른지 확인해주세요.\n\n[상세 오류 내용]"
      f" {error_message}"
  )
else:
  # 응답받은 데이터를 판다스 데이터프레임으로 변환
  df = pd.DataFrame(raw_data)

  # 숫자형 데이터(순위, 관객수, 누적관객수, 스크린수)를 문자열에서 정수(int)로 변환
  df["rank"] = df["rank"].astype(int)
  df["audiCnt"] = df["audiCnt"].astype(int)
  df["audiAcc"] = df["audiAcc"].astype(int)
  df["scrnCnt"] = df["scrnCnt"].astype(int)

  # --- [1위 영화 지표 카드 3장] ---
  top1 = df.iloc[0]
  st.markdown("---")
  st.subheader(f"🏆 어제의 1위 영화: **{top1['movieNm']}**")

  col1, col2, col3 = st.columns(3)
  col1.metric(
      label="일일 관객수",
      value=f"{top1['audiCnt']:,}명",
      delta=f"전날 대비 순위 증감: {top1['rankInten']}",
  )
  col2.metric(label="누적 관객수", value=f"{top1['audiAcc']:,}명")
  col3.metric(label="상영 스크린수", value=f"{top1['scrnCnt']:,}개")

  # --- [관객수 상위 5편 막대그래프] ---
  st.markdown("---")
  st.subheader("📊 관객수 상위 5편 비교")

  # 상위 5개 영화의 영화명과 관객수 추출 후 막대그래프 표시
  top5_df = df.head(5).copy()
  chart_data = top5_df.set_index("movieNm")["audiCnt"]
  st.bar_chart(chart_data)

  # --- [전체 박스오피스 순위 표] ---
  st.markdown("---")
  st.subheader("📋 전체 박스오피스 순위 표")

  # 사용자에게 보여줄 컬럼만 선택하고 컬럼명을 한글로 변경
  display_df = df[
      ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
  ].copy()
  display_df.columns = [
      "순위",
      "영화명",
      "개봉일",
      "관객수",
      "누적관객수",
      "스크린수",
  ]

  # 표 형태로 출력 (인덱스 숨기기)
  st.dataframe(display_df, use_container_width=True, hide_index=True)
