
import streamlit as st
import json
import re
from collections import Counter
import time

def edit_text_simple(label: str, key: str, original_text: str, height=80):
    current_value = st.session_state.get(key, original_text)
    st.markdown(f"**{label}**")
    updated = st.text_area("", value=current_value, key=key, height=height, label_visibility="collapsed")
    return updated

st.set_page_config(page_title="Multihop NLI Label Review", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.title("📂 File dữ liệu")
    uploaded_file = st.file_uploader("📤 Tải file JSON", type=["json"])
    export_filename = st.text_input("💾 Tên file xuất (.json)", value="updated_labeled.json")

if uploaded_file:
    data = json.load(uploaded_file)
    st.session_state.setdefault("edited_label", {})
    edited_examples = {}

    for example in data:
        raw_id = example.get("id", "")
        match = re.search(r'_(\d+)$', raw_id)
        clean_id = match.group(1) if match else raw_id
        example["clean_id"] = example.get("clean_id", clean_id)

        validated_labels = {
            k: v.strip().lower() for k, v in example.items()
            if k.endswith("_validated") and isinstance(v, str)
        }
        label_counts = Counter(validated_labels.values())
        model_votes = {k.split("/")[-2]: v.strip().lower() for k, v in validated_labels.items()}
        most_common = label_counts.most_common(1)
        auto_label = most_common[0][0] if most_common and most_common[0][1] >= 2 else None
        num_agree = most_common[0][1] if most_common else 0

        example["label"] = example.get("label", "")
        if clean_id in st.session_state["edited_label"]:
            final_label = st.session_state["edited_label"][clean_id]
            override_type = "manual"
        elif auto_label:
            final_label = auto_label
            override_type = "auto"
        else:
            final_label = None
            override_type = "manual"

        example["override_type"] = override_type
        example["original_label"] = example.get("original_label", example.get("label", "unknown"))
        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes
        example["final_label"] = final_label

    st.write("✅ File loaded và auto-label/final-label đã tính xong!")

    tab_groups = {
        "🧠 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "✍️ Manually assigned": [ex for ex in data if ex["override_type"] == "manual"],
    }

    for tab_name, examples in tab_groups.items():
        st.markdown(f"### {tab_name} — {len(examples)} mẫu")
        for ex in examples[:5]:
            st.markdown(f"- `{ex['id']}` → **{ex['final_label']}**")

else:
    st.info("📥 Vui lòng tải file JSON từ sidebar để bắt đầu.")
