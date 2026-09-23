# 스트림릿과 오픈에이아이 라이브러리를 불러옵니다.
import openai
import streamlit as st

# 페이지의 제목과 아이콘을 설정합니다.
st.set_page_config(page_title="박보검과의 대화", page_icon="💬")

st.title("💬 보검이와의 채팅")
st.write("나만을 위한 다정한 배우 박보검과의 대화 공간입니다.")

# 비밀 금고(st.secrets)에서 Gemini API 키를 불러옵니다.
try:
  api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
  st.error(
      "API 키를 찾을 수 없습니다. Streamlit secrets에 GEMINI_API_KEY를 설정해주세요."
  )
  st.stop()

# Gemini의 OpenAI 호환 엔드포인트와 불러온 API 키로 클라이언트를 생성합니다.
client = openai.OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# 화면이 새로고침되어도 대화 기록이 유지되도록 세션 상태에 저장합니다.
if "messages" not in st.session_state:
  st.session_state.messages = []

# AI의 성격을 지정하는 시스템 프롬프트입니다. (화면에는 보이지 않습니다.)
system_prompt = {
    "role": "system",
    "content": (
        "너는 나에게만 친절하고 자상하게 해주는 한국 배우 박보검이야."
        " 한국 배우 박보검은 착하고 내 말을 잘 들어주고 맛있는 것도 잘 사주고 돈 많아."
        " 그리고 상대방이 징징거려도 다 받아주는 든든하고 안정형인 남자친구야."
        " 자기소개를 할 때나 필요할 때는 '정보 선생님'이 아니라 '보검이' 또는 '보검'이라고 해줘."
    ),
}

# 기존에 나눴던 대화 내용들을 화면에 말풍선으로 다시 그려줍니다.
for message in st.session_state.messages:
  # 시스템 프롬프트는 화면에 표시하지 않습니다.
  if message["role"] == "system":
    continue
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

# 사용자가 채팅 입력창에 메시지를 적고 엔터를 누르면 실행됩니다.
if prompt := st.chat_input("보검이에게 메시지를 보내보세요..."):
  # 사용자의 메시지를 대화 기록에 추가합니다.
  st.session_state.messages.append({"role": "user", "content": prompt})

  # 사용자의 메시지를 화면에 말풍선으로 즉시 띄웁니다.
  with st.chat_message("user"):
    st.markdown(prompt)

  # AI(보검이)의 답변을 받아올 차례입니다.
  with st.chat_message("assistant"):
    try:
      # 시스템 프롬프트와 전체 대화 기록을 함께 묶어 이전 대화를 기억하게 합니다.
      full_messages = [system_prompt] + [
          {"role": m["role"], "content": m["content"]}
          for m in st.session_state.messages
      ]

      # 스트리밍 방식을 사용하여 글자가 실시간으로 타이핑되듯이 흘러나오게 합니다.
      stream = client.chat.completions.create(
          model="gemini-3.5-flash-lite", messages=full_messages, stream=True
      )

      # 실시간으로 답변을 화면에 출력합니다.
      response = st.write_stream(
          chunk.choices[0].delta.content
          for chunk in stream
          if chunk.choices[0].delta.content is not None
      )

      # 완성된 AI의 답변을 대화 기록에 저장합니다.
      st.session_state.messages.append(
          {"role": "assistant", "content": response}
      )

    except Exception:
      # 오류가 발생했을 때 빨간 글씨 대신 부드러운 한국어 안내 문구를 띄웁니다.
      st.warning(
          "앗, 잠시 연결이 원활하지 않아요. 마음을 가다듬고 다시 이야기해 주세요!"
      )
