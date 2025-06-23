import streamlit as st
import json
from collections import Counter
import re

st.set_page_config(
    page_title="Multihop NLI Label Review App",
    layout="wide",
    initial_sidebar_state="expanded",  # Sidebar mở mặc định
)

# Sidebar Navigation
with st.sidebar:
    st.title("🧭 Điều hướng")
    selected_section = st.radio("Chọn chức năng:", ["📤 Import dữ liệu", "🔍 Gán nhãn", "💾 Export kết quả"])

# 👉 Chế độ sáng/tối do người dùng chọn trong ⚙️ góc phải (Streamlit theme setting)
st.caption("🌗 Dùng ⚙️ ở góc phải để chuyển sáng/tối")

# 🟦 Biến toàn cục
data = []
edited_examples = {}

# 📤 Nhập dữ liệu
if selected_section == "📤 Import dữ liệu":
    st.header("📤 Tải dữ liệu JSON")
    uploaded_file = st.file_uploader("Chọn file JSON đã được gán nhãn", type=["json"])
    if uploaded_file:
        data = json.load(uploaded_file)
        st.session_state["data_loaded"] = True
        st.session_state["raw_data"] = data
        st.success(f"✅ Đã tải {len(data)} mẫu.")

# 💾 Xuất dữ liệu
elif selected_section == "💾 Export kết quả":
    st.header("💾 Tải dữ liệu đã chỉnh sửa")
    if st.session_state.get("data_loaded"):
        filename = st.text_input("Tên file xuất (.json)", value="updated_labeled.json")
        if st.button("📥 Tải xuống"):
            raw_data = st.session_state.get("raw_data", [])
            json_str = json.dumps(raw_data, ensure_ascii=False, indent=2)
            st.download_button("📥 Click để tải JSON",
                               data=json_str.encode("utf-8"),
                               file_name=filename,
                               mime="application/json")
    else:
        st.warning("⚠️ Bạn cần import dữ liệu trước.")

# 🔍 Giao diện chính gán nhãn
elif selected_section == "🔍 Gán nhãn":
    st.header("🔍 Giao diện gán nhãn")
    if not st.session_state.get("data_loaded"):
        st.warning("⚠️ Vui lòng tải file JSON trước trong tab '📤 Import dữ liệu'")
    else:
        st.success(f"✅ Đang làm việc với {len(st.session_state['raw_data'])} mẫu.")
        # Ở đây bạn có thể chèn lại phần tabs logic như ở trên
