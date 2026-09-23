# 스트림릿과 오픈에이아이 라이브러리를 불러옵니다.
import openai
import streamlit as st

# 페이지의 제목을 설정합니다.
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

# 화면 새로고침(재실행) 시에도 대화 기록이 유지되도록 세션 상태에 저장합니다.
if "messages" not in st.session_state:
  st.session_state.messages = []

# 시스템 프롬프트(AI의 성격 부여)를 대화 기록의 맨 처음에 설정합니다. (화면에는 노출되지 않음)
system_prompt = {
    "role": "system",
    "content": (
        "너는 나에게만 친절하고 자상하게 해주는 한국 배우 박보검이야."
        " 한국 배우 박보검은 착하고 내 말을 잘 들어주고 맛있는 것도 잘 사주고 돈 많아."
    ),
}

# 기존에 나눴던 대화 기록들을 화면에 말풍선으로 다시 그려줍니다.
for message in st.session_state.messages:
  # 시스템 프롬프트는 화면에 보여주지 않고 건너뜁니다.
  if message["role"] == "system":
    continue
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

# 사용자가 채팅 입력창에 메시지를 입력하면 실행됩니다.
if prompt := st.chat_input("보검이에게 메시지를 보내보세요..."):
  # 사용자가 보낸 메시지를 대화 기록에 추가합니다.
  st.session_state.messages.append({"role": "user", "content": prompt})

  # 사용자의 메시지를 화면에 말풍선으로 즉시 표시합니다.
  with st.chat_message("user"):
    st.markdown(prompt)

  # AI(보검이)의 답변을 출력할 차례입니다.
  with st.chat_message("assistant"):
    try:
      # 시스템 프롬프트와 전체 대화 기록을 함께 전달하여 이전 대화를 기억하게 합니다.
      full_messages = [system_prompt] + [
          {"role": m["role"], "content": m["content"]}
          for m in st.session_state.messages
      ]

      # 요청이 실패하지 않도록 글자 단위로 실시간 출력(스트리밍)을 설정합니다.
      stream = client.chat.completions.create(
          model="gemini-3.5-flash-lite", messages=full_messages, stream=True
      )

      # AI의 답변을 실시간으로 화면에 흘러나오게 보여줍니다.
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
      # 오류 발생 시 빨간 에러 화면 대신 친절한 한국어 안내 문구를 띄웁니다.
      st.warning(
          "앗, 잠시 연결이 원활하지 않아요. 마음을 가다듬고 다시 이야기해 주세요!"
      )
