import streamlit as st
import json
from collections import Counter
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("🔍 Multihop NLI Label Review App")

uploaded_file = st.sidebar.file_uploader("📤 Upload labeled JSON file", type=["json"])

# Inject JavaScript to listen to keypress events and update Streamlit session state
components.html("""
<script>
document.addEventListener("keydown", function(e) {
    if (e.key === "d" || e.key === "D") {
        window.parent.postMessage({ isStreamlitMessage: true, type: "streamlit:setComponentValue", key: "quick_key", value: "next" }, "*");
    }
    if (e.key === "s" || e.key === "S") {
        window.parent.postMessage({ isStreamlitMessage: true, type: "streamlit:setComponentValue", key: "quick_key", value: "prev" }, "*");
    }
});
</script>
""", height=0)

if uploaded_file:
    data = json.load(uploaded_file)
    st.success(f"Loaded {len(data)} examples.")

    edited_examples = {}

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

    mode = st.sidebar.radio("🛠️ Chế độ hiển thị", ["📄 Phân trang", "⚡ Quick review"])
    filtered_data = data

    if mode == "📄 Phân trang":
        page_size = 10
        total = len(filtered_data)
        total_pages = (total - 1) // page_size + 1
        current_page = st.sidebar.number_input("📄 Page", min_value=1, max_value=total_pages, step=1)

        start = (current_page - 1) * page_size
        end = min(start + page_size, total)
        st.markdown(f"### 📊 Hiển thị mẫu {start + 1}–{end} / {total}")

        for example in filtered_data[start:end]:
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

            st.markdown("**🧠 Model votes:**")
            for model, vote in model_votes.items():
                st.markdown(f"- `{model}` → **{vote}**")

            with st.expander("✏️ Chỉnh nhãn"):
                key = f"edit_{example_id}"
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
            col1.markdown(f"**🔖 Original:** `{original_label}`")
            col2.markdown(f"**🤖 Auto:** `{auto_label or 'None'}`")
            col3.markdown(f"**👤 Final:** `{current_label}`{final_note}")

    elif mode == "⚡ Quick review":
        total = len(filtered_data)
        if "quick_index" not in st.session_state:
            st.session_state.quick_index = 0

        # Handle keypress events from JS
        if "quick_key" in st.session_state:
            if st.session_state.quick_key == "prev" and st.session_state.quick_index > 0:
                st.session_state.quick_index -= 1
            if st.session_state.quick_key == "next" and st.session_state.quick_index < total - 1:
                st.session_state.quick_index += 1
            del st.session_state.quick_key

        col_prev, col_jump, col_next = st.columns([1, 4, 1])
        with col_prev:
            if st.button("⏪ Prev") and st.session_state.quick_index > 0:
                st.session_state.quick_index -= 1
        with col_jump:
            st.number_input("🔢 Jump to index", 0, total - 1, key="quick_index", step=1)
        with col_next:
            if st.button("⏩ Next") and st.session_state.quick_index < total - 1:
                st.session_state.quick_index += 1

        example = filtered_data[st.session_state.quick_index]
        example_id = example["id"]
        premises = example["premises"]
        hypothesis = example["hypothesis"]
        original_label = example["original_label"]
        auto_label = example["auto_label"]
        model_votes = example["model_votes"]
        current_label = edited_examples.get(example_id, example["label"])

        st.markdown("---")
        st.markdown(f"**🧾 ID:** `{example_id}`")
        for j, p in enumerate(premises):
            st.markdown(f"**Premise {j+1}:** {p}")
        st.markdown(f"**🔮 Hypothesis:** {hypothesis}")

        st.markdown("**🧠 Model votes:**")
        for model, vote in model_votes.items():
            st.markdown(f"- `{model}` → **{vote}**")

        with st.expander("✏️ Chỉnh nhãn"):
            key = f"quick_edit_{example_id}"
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
        col1.markdown(f"**🔖 Original:** `{original_label}`")
        col2.markdown(f"**🤖 Auto:** `{auto_label or 'None'}`")
        col3.markdown(f"**👤 Final:** `{current_label}`{final_note}")

    st.sidebar.markdown("## 💾 Export kết quả")
    filename = st.sidebar.text_input("Tên file xuất (.json)", value="updated_labeled.json")

    if st.sidebar.button("📥 Tải về JSON"):
        for example in data:
            example_id = example["id"]
            if example_id in edited_examples:
                example["label"] = edited_examples[example_id]
                example["override_type"] = (
                    "manual" if example["label"] != example["auto_label"] else "auto"
                )

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.sidebar.download_button(
            label="💾 Click để tải JSON",
            file_name=filename,
            mime="application/json",
            data=json_str.encode("utf-8"),
        )
