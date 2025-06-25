import streamlit as st
import json
import re
from collections import Counter
import time

def edit_text_simple(label: str, key: str, original_text: str, height=80):
    if key not in st.session_state:
        st.session_state[key] = original_text
    st.markdown(f"**{label}**")
    st.text_area("", key=key, height=height, label_visibility="collapsed")
    return st.session_state[key]

st.set_page_config(page_title="Multihop NLI Label Review", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.title("📂 File dữ liệu")
    uploaded_file = st.file_uploader("📤 Tải file JSON", type=["json"])
    export_filename = st.text_input("💾 Tên file xuất (.json)", value="updated_labeled.json")

if uploaded_file:
    data = json.load(uploaded_file)
    st.session_state.setdefault("edited_premises", {})
    st.session_state.setdefault("edited_hypothesis", {})
    st.session_state.setdefault("edited_label", {})

    for example in data:
        raw_id = example.get("id", "")
        match = re.search(r'_(\d+)$', raw_id)
        clean_id = match.group(1) if match else raw_id
        example["clean_id"] = clean_id

        validated_labels = {k: v for k, v in example.items() if k.endswith("_validated")}
        label_counts = Counter(validated_labels.values())
        model_votes = {k.split("/")[-2]: v for k, v in validated_labels.items()}
        most_common = label_counts.most_common(1)
        auto_label = most_common[0][0] if most_common and most_common[0][1] >= 2 else None
        num_agree = most_common[0][1] if most_common else 0

        example["label"] = example.get("label", "")
        example["override_type"] = "auto" if auto_label else "manual"
        example["original_label"] = example.get("original_label", example.get("label", "unknown"))
        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    tab_names = ["Tất cả"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.markdown(f"### 📊 Tổng số mẫu: {len(data)}")
        index_key = "main_index"
        st.session_state.setdefault(index_key, 0)

        col1, col2 = st.columns([5, 5])
        with col1:
            search_id = st.text_input("🔎 Tìm theo ID", key="search_id")
        with col2:
            goto_page = st.number_input("🔢 Đi đến vị trí", 1, max(1, len(data)), 1, key="goto_index")

        if st.button("🚀 Tìm / Chuyển trang", key="search_btn"):
            found = False
            if search_id:
                for idx, ex in enumerate(data):
                    if ex["clean_id"] == search_id:
                        st.session_state[index_key] = idx
                        st.success(f"🔍 Tìm thấy ID `{search_id}` tại vị trí {idx+1}/{len(data)}")
                        found = True
                        break
                if not found:
                    st.warning("❌ Không tìm thấy ID.")
            else:
                st.session_state[index_key] = int(goto_page) - 1

        if len(data) == 0:
            st.info("Không có mẫu nào.")
        else:
            nav_left, main_col, nav_right = st.columns([1, 10, 1])
            with nav_left:
                if st.button("◀️", key="prev"):
                    st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
            with nav_right:
                if st.button("▶️", key="next"):
                    st.session_state[index_key] = min(len(data) - 1, st.session_state[index_key] + 1)

            current_index = st.session_state[index_key]
            example = data[current_index]

            with main_col:
                st.markdown("---")
                st.markdown(f"🧾 **ID:** `{example['id']}` → `{example['clean_id']}` ({current_index+1}/{len(data)})")

                updated_premises = []
                for j, p in enumerate(example.get("premises", [])):
                    field_key = f"{example['clean_id']}_premise_{j}"
                    edit_text_simple(f"Premise {j+1}:", field_key, p)
                    updated_premises.append(st.session_state[field_key])
                st.session_state["edited_premises"][example["clean_id"]] = updated_premises

                hyp_key = f"{example['clean_id']}_hypothesis"
                edit_text_simple("Hypothesis:", hyp_key, example.get("hypothesis", ""))
                st.session_state["edited_hypothesis"][example["clean_id"]] = st.session_state[hyp_key]

                st.markdown("#### 🧠 Model votes:")
                for model, vote in example.get("model_votes", {}).items():
                    st.markdown(f"- `{model}` → **{vote}**")

                with st.expander("✏️ Chỉnh nhãn thủ công"):
                    override = st.selectbox(
                        "Chọn nhãn mới:",
                        ["", "entailment", "contradiction", "neutral", "implicature"],
                        key=f"{example['clean_id']}_override"
                    )
                    if override:
                        st.session_state["edited_label"][example["clean_id"]] = override

                auto_label = example.get("auto_label")
                final_label = st.session_state["edited_label"].get(example["clean_id"], auto_label or example["label"])
                note = (
                    " (auto-assigned)" if final_label == auto_label
                    else " (overridden manually)" if auto_label
                    else " (manual)"
                )
                st.markdown(f"**👤 Final label:** `{final_label}`{note}")

    # ✅ Ghi dữ liệu vào file khi export
    with st.sidebar:
        for example in data:
            clean_id = example["clean_id"]
            if clean_id in st.session_state["edited_premises"]:
                example["premises"] = st.session_state["edited_premises"][clean_id]
            if clean_id in st.session_state["edited_hypothesis"]:
                example["hypothesis"] = st.session_state["edited_hypothesis"][clean_id]
            example["final_label"] = st.session_state["edited_label"].get(
                clean_id, example.get("auto_label") or example.get("label")
            )

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("📥 Tải file kết quả", data=json_str.encode("utf-8"),
                           file_name=export_filename, mime="application/json")

# 🔁 Reload tự động sau 60 giây (giúp tránh ngắt session trên Streamlit Cloud)
if uploaded_file:
    time.sleep(60)
    st.rerun()
