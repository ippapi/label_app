import streamlit as st
import json
from collections import Counter

st.set_page_config(layout="wide")
st.title("🔍 Multihop NLI Label Review App")

uploaded_file = st.file_uploader("📤 Upload labeled JSON file", type=["json"])

if uploaded_file:
    data = json.load(uploaded_file)
    st.success(f"Loaded {len(data)} examples.")

    # Gán nhãn auto/manual
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
                auto_label = None
                num_agree = vote_count
                example["override_type"] = "manual"
        else:
            auto_label = None
            example["override_type"] = "manual"

        if "original_label" not in example:
            example["original_label"] = example["label"]

        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    tab_groups = {
        "🧠 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "✍️ Manually assigned": [ex for ex in data if ex["override_type"] == "manual" and ex["auto_label"] is not None and ex["label"] != ex["auto_label"]],
        "✅ 3/3 models agree": [ex for ex in data if ex["num_agree"] == 3],
        "⚠️ 2/3 models agree": [ex for ex in data if ex["num_agree"] == 2],
        "❌ 1/3 or all different": [ex for ex in data if ex["num_agree"] <= 1],
        "🟩 entailment": [ex for ex in data if ex["label"] == "entailment"],
        "🟥 contradiction": [ex for ex in data if ex["label"] == "contradiction"],
        "🟨 neutral": [ex for ex in data if ex["label"] == "neutral"],
        "🟦 implicature": [ex for ex in data if ex["label"] == "implicature"],
    }

    tabs = st.tabs(list(tab_groups.keys()))

    # Script để bắt phím A/D
    st.markdown("""
    <script>
    document.addEventListener("keydown", function(event) {
        if (event.key === "a" || event.key === "A") {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'prev'}, "*");
        } else if (event.key === "d" || event.key === "D") {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'next'}, "*");
        }
    });
    </script>
    """, unsafe_allow_html=True)

    # Hack JS -> Python using components
    from streamlit.components.v1 import declare_component
    nav_control = declare_component("nav_control", url="")

    for i, (tab_name, subset) in enumerate(tab_groups.items()):
        with tabs[i]:
            if len(subset) == 0:
                st.info("Không có mẫu nào trong tab này.")
                continue

            session_key = f"index_{tab_name}"
            if session_key not in st.session_state:
                st.session_state[session_key] = 0

            # Nhận event từ JS
            action = nav_control(key=f"{tab_name}_nav")

            if action == "prev":
                st.session_state[session_key] = max(0, st.session_state[session_key] - 1)
            elif action == "next":
                st.session_state[session_key] = min(len(subset) - 1, st.session_state[session_key] + 1)

            current_index = st.session_state[session_key]
            current_example = subset[current_index]

            st.markdown(f"### 📊 Tổng số mẫu: `{len(subset)}` — Đang xem mẫu `{current_index + 1}`")

            example_id = current_example["id"]
            premises = current_example["premises"]
            hypothesis = current_example["hypothesis"]
            original_label = current_example["original_label"]
            auto_label = current_example["auto_label"]
            model_votes = current_example["model_votes"]
            current_label = edited_examples.get(example_id, current_example["label"])

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

    # Export
    st.markdown("## 💾 Export kết quả")
    filename = st.text_input("Tên file xuất (.json)", value="updated_labeled.json")

    if st.button("💾 Tải về JSON"):
        for example in data:
            example_id = example["id"]
            if example_id in edited_examples:
                example["label"] = edited_examples[example_id]
                example["override_type"] = ("manual" if example["label"] != example["auto_label"] else "auto")

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Click để tải JSON",
            file_name=filename,
            mime="application/json",
            data=json_str.encode("utf-8"),
        )
