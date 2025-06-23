import streamlit as st
import json
import re
from collections import Counter

# 🎨 App config
st.set_page_config(
    page_title="Multihop NLI Label Review",
    layout="wide",
    initial_sidebar_state="expanded",  # Always show sidebar
)

# 🌐 Sidebar (Import / Export đều nằm ở đây)
with st.sidebar:
    st.title("🧭 Điều hướng")

    uploaded_file = st.file_uploader("📤 Tải file JSON", type=["json"])
    export_filename = st.text_input("💾 Tên file xuất (.json)", value="updated_labeled.json")
    export_trigger = st.button("📥 Tải xuống file kết quả")

# 🧠 Data processing nếu file được upload
if uploaded_file:
    data = json.load(uploaded_file)
    st.session_state["data_loaded"] = True
    edited_examples = {}

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

        example["label"] = auto_label if auto_label else example.get("label", "")
        example["override_type"] = "auto" if auto_label else "manual"
        example["original_label"] = example.get("original_label", example.get("label", "unknown"))
        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    if export_trigger:
        for example in data:
            cid = example["clean_id"]
            if cid in edited_examples:
                example["label"] = edited_examples[cid]
                example["override_type"] = "manual" if example["label"] != example["auto_label"] else "auto"
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("📥 Click để tải JSON", data=json_str.encode("utf-8"),
                           file_name=export_filename, mime="application/json")

    # Tabs logic
    tab_groups = {
        "🧠 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "✍️ Manually assigned": [
            ex for ex in data if ex["override_type"] == "manual"
            and ex["auto_label"] is not None and ex["label"] != ex["auto_label"]
        ],
        "✅ 3/3 models agree": [ex for ex in data if ex["num_agree"] == 3],
        "⚠️ 2/3 models agree": [ex for ex in data if ex["num_agree"] == 2],
        "❌ 1/3 or all different": [ex for ex in data if ex["num_agree"] <= 1],
        "🟩 entailment": [ex for ex in data if ex["label"] == "entailment"],
        "🟥 contradiction": [ex for ex in data if ex["label"] == "contradiction"],
        "🟨 neutral": [ex for ex in data if ex["label"] == "neutral"],
        "🟦 implicature": [ex for ex in data if ex["label"] == "implicature"],
    }

    tabs = st.tabs(list(tab_groups.keys()))

    for i, (tab_name, subset) in enumerate(tab_groups.items()):
    with tabs[i]:
        st.markdown(f"### 📊 Số lượng mẫu: {len(subset)}")

        index_key = f"{tab_name}_index"
        if index_key not in st.session_state:
            st.session_state[index_key] = 0

        if len(subset) == 0:
            st.info("Không có mẫu nào trong tab này.")
            continue

        # Navigation bằng < và >
        nav_left, main_col, nav_right = st.columns([1, 10, 1])
        with nav_left:
            if st.button("◀️", key=f"{tab_name}_prev"):
                st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
        with nav_right:
            if st.button("▶️", key=f"{tab_name}_next"):
                st.session_state[index_key] = min(len(subset) - 1, st.session_state[index_key] + 1)

        # Giới hạn index
        st.session_state[index_key] = max(0, min(st.session_state[index_key], len(subset) - 1))
        example = subset[st.session_state[index_key]]
        current_index = st.session_state[index_key]

        with main_col:
            st.markdown("---")
            st.markdown(f"🧾 **ID:** `{example['id']}` → `{example['clean_id']}` ({current_index+1}/{len(subset)})")

            for j, p in enumerate(example.get("premises", [])):
                st.markdown(
                    f"<div style='font-size: 0.85rem; margin-bottom: 6px;'>"
                    f"<b>Premise {j+1}:</b> {p}</div>",
                    unsafe_allow_html=True
                )

            st.markdown(f"**🔮 Hypothesis:** {example.get('hypothesis', '')}")

            st.markdown("#### 🧠 Model votes:")
            for model, vote in example.get("model_votes", {}).items():
                st.markdown(f"- `{model}` → **{vote}**")

            with st.expander("✏️ Chỉnh nhãn thủ công"):
                override = st.selectbox(
                    "Chọn nhãn mới:",
                    ["", "entailment", "contradiction", "neutral", "implicature"],
                    key=f"{tab_name}_{example['clean_id']}_override"
                )
                if override:
                    edited_examples[example["clean_id"]] = override

            auto_label = example.get("auto_label")
            current_label = edited_examples.get(example["clean_id"], example["label"])
            final_note = (
                " (no auto-assigned)" if auto_label is None
                else " (auto-assigned)" if current_label == auto_label
                else " (overridden manually)"
            )

            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**🔖 Original label:** `{example.get('original_label', 'N/A')}`")
            col2.markdown(f"**🤖 Auto-assigned:** `{auto_label or 'None'}`")
            col3.markdown(f"**👤 Final label:** `{current_label}`{final_note}")
else:
    st.info("📥 Vui lòng tải file JSON từ sidebar để bắt đầu.")
