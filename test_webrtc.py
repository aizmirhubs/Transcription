import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

st.title("Streamlit WebRTC Test")

st.write("Bu bir ses ve video kaydı testidir.")

webrtc_ctx = webrtc_streamer(
    key="test",
    mode=WebRtcMode.RECVONLY,  # Enum kullanımı: WebRtcMode.RECVONLY
    media_stream_constraints={
        "audio": True,
        "video": False,  # Video kaydı gerekiyorsa True yapabilirsiniz
    },
)

if webrtc_ctx and webrtc_ctx.state.playing:
    st.success("Ses kaydı yapılıyor. Mikrofon erişimi verildi.")
else:
    st.warning("Ses kaydı başlatılamadı. Mikrofon erişimine izin verin.")
