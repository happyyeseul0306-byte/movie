from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# 1. 스트림릿 페이지 기본 설정 (와이드 레이아웃 적용)
st.set_page_config(
    page_title="어제 기준 박스오피스 & 간식 추천", page_icon="🎬", layout="wide"
)

st.title("🎬 어제의 영화 박스오피스 & 맞춤 간식 추천")
st.markdown(
    "영화진흥위원회(KOBIS) 공식 API를 활용하여 한국 시간 기준 어제의 박스오피스"
    " 순위를 확인하고, 영화별 추천 간식을 만나보세요!"
)

# 2. 한국 시간(KST, UTC+9) 기준으로 '어제' 날짜 자동 계산하기
# (스트림릿 클라우드 서버는 기본적으로 UTC 기준이므로 시간대를 맞추어야 합니다)
kst = timezone(timedelta(hours=9))
yesterday = datetime.now(kst) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

# 화면에 보여줄 날짜 포맷 (예: 2026년 09월 22일)
display_date = f"{target_dt[:4]}년 {target_dt[4:6]}월 {target_dt[6:]}일"
st.info(f"📅 조회 기준일: **{display_date}** (한국 시간 기준 어제)")


# 3. KOBIS API 데이터 호출 함수
@st.cache_data(ttl=3600)  # 데이터를 1시간 동안 캐시하여 불필요한 API 요청 방지
def fetch_box_office_data(date_str):
  # 비밀 금고(secrets)에서 KOBIS_KEY 불러오기
  try:
    api_key = st.secrets["KOBIS_KEY"]
  except Exception:
    return None, (
        "Secret 설정 오류: Streamlit Cloud의 Settings > Secrets에 'KOBIS_KEY'"
        "가 등록되어 있는지 확인해주세요."
    )

  # 공식 문서에 안내된 요청 주소
  url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
  params = {"key": api_key, "targetDt": date_str}

  try:
    response = requests.get(url, params=params)
    data = response.json()

    # KOBIS API는 인증키가 틀려도 200 코드를 주며 대신 faultInfo 상자를 반환함
    if "faultInfo" in data:
      return (
          None,
          f"API 인증 오류 (faultInfo): {data['faultInfo']}\n시크릿 금고에"
          " 입력된 인증키가 올바른지 확인해주세요.",
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
        f"요청 중 오류가 발생했습니다: {e}\n인터넷 연결 상태를 확인해주세요.",
    )


# 4. 데이터 불러오기 실행
raw_data, error_message = fetch_box_office_data(target_dt)

# 5. 요청이 실패하거나, 오류 상자가 오거나, 영화 목록이 비어 있을 때 안내문 출력
if error_message:
  st.error(
      "⚠️ **데이터를 불러오지 못했습니다.**\n\n확인해야 할"
      f" 사항:\n- {error_message}\n- Streamlit Cloud 앱 설정(Settings >"
      " Secrets)에 `KOBIS_KEY`가 올바르게 입력되었는지 확인해주세요.\n- 어제"
      " 날짜의 박스오피스 데이터가 아직 완전히 집계되지 않았을 수도 있습니다."
  )
else:
  # 응답받은 데이터를 판다스 데이터프레임으로 변환
  df = pd.DataFrame(raw_data)

  # 숫자 값들이 문자열로 오므로 필요한 컬럼들을 정수(int)로 변환
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

  # --- [영화별 맞춤 간식 추천 기능] ---
  st.markdown("---")
  st.subheader("🍿 영화 선택별 맞춤 간식 추천")
  st.markdown(
      "아래 목록에서 영화를 선택하면, 해당 영화와 함께 즐기기 좋은 맛있는"
      " 간식을 추천해 드립니다!"
  )

  # 영화 제목 목록을 셀렉트박스 옵션으로 생성
  movie_options = df["movieNm"].tolist()
  selected_movie = st.selectbox(
      "관람할 영화를 선택하세요 (박스오피스 순위권)", movie_options
  )


  # 영화 키워드 또는 분위기에 따른 간식 추천 함수
  def get_snack_recommendation(movie_name):
    if any(
        word in movie_name for word in ["액션", "범죄", "스릴러", "작전", "도시"]
    ):
      return (
          "🔥 매콤한 **국물 떡볶이와 바삭한 모둠 튀김**\n> 짜릿하고 긴장감 넘치는"
          " 액션 영화에는 입맛을 돋우는 매운맛이 제격이죠!"
      )
    elif any(
        word in movie_name for word in ["애니", "소닉", "인사이드", "모험"]
    ):
      return (
          "🍿 달콤고소한 **카라멜 팝콘과 시원한 에이드**\n> 온 가족이 함께 즐기는"
          " 애니메이션에는 달달한 팝콘이 최고입니다!"
      )
    elif any(
        word in movie_name for word in ["공포", "오컬트", "사바하", "파묘"]
    ):
      return (
          "🧊 시원한 **얼음 콜라와 매콤한 나초 치즈 콤보**\n> 간담이 서늘해지는"
          " 공포 영화를 보며 긴장감을 달래보세요!"
      )
    else:
      return (
          "🧈 영화관의 영원한 베스트셀러 **버터구이 오징어와 고소한"
          " 팝콘**\n> 클래식은 언제나 실패하지 않는 완벽한 조합입니다!"
      )


  # 선택된 영화에 대한 간식 추천 출력
  snack_result = get_snack_recommendation(selected_movie)
  st.success(f"🎬 **{selected_movie}** 관람 추천 간식\n\n{snack_result}")

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

  # 요구하신 순위·영화명·개봉일·관객수·누적관객·스크린수 컬럼 선택 및 이름 변경
  display_df = df[
      ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
  ].copy()
  display_df.columns = [
      "순위",
      "영화명",
      "개봉일",
      "관객수",
      "누적관객",
      "스크린수",
  ]

  # 표 형태로 깔끔하게 출력 (인덱스 숨기기)
  st.dataframe(display_df, use_container_width=True, hide_index=True)
