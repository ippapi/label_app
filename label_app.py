import streamlit as st
import json
from collections import Counter

st.set_page_config(layout="wide")
st.title("🔍 Multihop NLI Label Review App")

# ⏫ Sidebar: Import file
st.sidebar.header("📤 Import & Tabs")
uploaded_file = st.sidebar.file_uploader("Upload labeled JSON", type=["json"])

if uploaded_file:
    data = json.load(uploaded_file)
    st.success(f"✅ Đã tải {len(data)} mẫu.")

    edited_examples = {}

    # Gán nhãn tự động
    for example in data:
        validated_labels = {k: v for k, v in example.items() if k.endswith("_validated")}
        label_counts = Counter(validated_labels.values())
        model_votes = {k.split("/")[-2]: v for k, v in validated_labels.items()}

        most_common = label_counts.most_common(1)
        auto_label = None
        num_agree = 0

        if most_common:
            candidate_label, vote_count = most_common[0]
            if vote_count >= 2:
                auto_label = candidate_label
                num_agree = vote_count
                example["label"] = auto_label
                example["override_type"] = "auto"
            else:
                example["override_type"] = "manual"
        else:
            example["override_type"] = "manual"

        if "original_label" not in example:
            example["original_label"] = example["label"]

        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    # ⏩ Sidebar: chọn nhóm mẫu
    tab_name = st.sidebar.selectbox("📂 Chọn nhóm mẫu", [
        "🧠 Auto-assigned",
        "✍️ Manually assigned",
        "✅ 3/3 models agree",
        "⚠️ 2/3 models agree",
        "❌ 1/3 or all different",
        "🟩 entailment",
        "🟥 contradiction",
        "🟨 neutral",
        "🟦 implicature",
    ])

    group_filters = {
        "🧠 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "✍️ Manually assigned": [
            ex for ex in data if ex["override_type"] == "manual" and ex["auto_label"] is not None and ex["label"] != ex["auto_label"]
        ],
        "✅ 3/3 models agree": [ex for ex in data if ex["num_agree"] == 3],
        "⚠️ 2/3 models agree": [ex for ex in data if ex["num_agree"] == 2],
        "❌ 1/3 or all different": [ex for ex in data if ex["num_agree"] <= 1],
        "🟩 entailment": [ex for ex in data if ex["label"] == "entailment"],
        "🟥 contradiction": [ex for ex in data if ex["label"] == "contradiction"],
        "🟨 neutral": [ex for ex in data if ex["label"] == "neutral"],
        "🟦 implicature": [ex for ex in data if ex["label"] == "implicature"],
    }

    filtered_data = group_filters[tab_name]
    total = len(filtered_data)
    st.markdown(f"### 📊 Số lượng mẫu: `{total}`")

    # Pagination
    page_size = 1
    max_page = (total - 1) // page_size + 1
    if "page" not in st.session_state:
        st.session_state.page = 1

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅️ Prev") and st.session_state.page > 1:
            st.session_state.page -= 1
    with col_info:
        st.markdown(f"### 📄 Trang `{st.session_state.page}` / `{max_page}`")
    with col_next:
        if st.button("Next ➡️") and st.session_state.page < max_page:
            st.session_state.page += 1

    # Hiển thị example hiện tại
    start_idx = (st.session_state.page - 1) * page_size
    end_idx = start_idx + page_size
    current_examples = filtered_data[start_idx:end_idx]

    for example in current_examples:
        st.markdown("---")
        example_id = example["id"]
        premises = example["premises"]
        hypothesis = example["hypothesis"]
        original_label = example["original_label"]
        auto_label = example["auto_label"]
        model_votes = example["model_votes"]
        current_label = edited_examples.get(example_id, example["label"])

        st.markdown(f"**🧾 ID:** `{example_id}`")
        for j, p in enumerate(premises):
            st.markdown(f"**Premise {j+1}:** {p}")
        st.markdown(f"**🔮 Hypothesis:** {hypothesis}")

        st.markdown("#### 🧠 Model votes:")
        for model, vote in model_votes.items():
            st.markdown(f"- `{model}` → **{vote}**")

        with st.expander("✏️ Chỉnh nhãn thủ công (nếu cần)"):
            key = f"{tab_name}_{example_id}_override"
            override = st.selectbox(
                "Chọn nhãn mới:",
                ["", "entailment", "contradiction", "neutral", "implicature"],
                key=key,
            )
            if override:
                current_label = override
                edited_examples[example_id] = override

        if auto_label is None:
            final_note = " (no auto-assigned label)"
        elif current_label == auto_label:
            final_note = " (auto-assigned)"
        else:
            final_note = " (overridden manually)"

        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**🔖 Original label:** `{original_label}`")
        col2.markdown(f"**🤖 Auto-assigned:** `{auto_label if auto_label else 'None'}`")
        col3.markdown(f"**👤 Final label:** `{current_label}`{final_note}")

    # ⬇️ Sidebar: Export
    st.sidebar.header("💾 Export")
    filename = st.sidebar.text_input("Tên file xuất (.json)", value="updated_labeled.json")

    if st.sidebar.button("💾 Tải về JSON"):
        for example in data:
            example_id = example["id"]
            if example_id in edited_examples:
                example["label"] = edited_examples[example_id]
                example["override_type"] = (
                    "manual" if example["label"] != example["auto_label"] else "auto"
                )

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.sidebar.download_button(
            label="📥 Click để tải JSON",
            file_name=filename,
            mime="application/json",
            data=json_str.encode("utf-8"),
        )
