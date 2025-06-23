import streamlit as st
import json
from collections import Counter
import re

st.set_page_config(layout="wide")
st.title("🔍 Multihop NLI Label Review App")

uploaded_file = st.file_uploader("📤 Upload labeled JSON file", type=["json"])

if uploaded_file:
    data = json.load(uploaded_file)
    st.success(f"Loaded {len(data)} examples.")
    edited_examples = {}

    # Chuẩn hóa clean_id (số cuối)
    for example in data:
        raw_id = example.get("id", "")
        match = re.search(r'_(\d+)$', raw_id)
        clean_id = match.group(1) if match else raw_id
        example["clean_id"] = clean_id

        # Label logic
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
                num_agree = vote_count
        else:
            example["override_type"] = "manual"

        if "original_label" not in example:
            example["original_label"] = example.get("label", "unknown")

        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    # Export section (top)
    with st.expander("💾 Export kết quả", expanded=True):
        filename = st.text_input("Tên file xuất (.json)", value="updated_labeled.json")

        if st.button("💾 Tải về JSON"):
            for example in data:
                cid = example["clean_id"]
                if cid in edited_examples:
                    example["label"] = edited_examples[cid]
                    example["override_type"] = (
                        "manual" if example["label"] != example["auto_label"] else "auto"
                    )
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            st.download_button("📥 Click để tải JSON", data=json_str.encode("utf-8"),
                               file_name=filename, mime="application/json")

    # Tabs
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
            st.markdown(f"### 📊 Số lượng mẫu: `{len(subset)}`")

            index_key = f"{tab_name}_index"
            if index_key not in st.session_state:
                st.session_state[index_key] = 0

            if len(subset) == 0:
                st.info("Không có mẫu nào trong tab này.")
                continue

            # Tìm theo clean_id (chỉ số)
            with st.expander("🔎 Tìm theo ID (chỉ nhập số sau dấu `_`)"):
                search_clean_id = st.text_input("Nhập ID (ví dụ: 1739):", key=f"{tab_name}_search")
                if search_clean_id:
                    found_idx = next(
                        (i for i, ex in enumerate(subset) if ex.get("clean_id") == search_clean_id),
                        None
                    )
                    if found_idx is not None:
                        st.success(f"🔍 Tìm thấy mẫu ở vị trí {found_idx+1}")
                        st.session_state[index_key] = found_idx
                    else:
                        st.warning("❗ Không tìm thấy ID này trong tab hiện tại.")

            # A/D control
            key_input = st.text_input("⎆ Nhập A hoặc D để chuyển mẫu", key=f"{tab_name}_key")
            if key_input.lower() == "a":
                st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
            elif key_input.lower() == "d":
                st.session_state[index_key] = min(len(subset) - 1, st.session_state[index_key] + 1)

            st.session_state[index_key] = max(0, min(st.session_state[index_key], len(subset) - 1))

            # Navigation
            colA, colB, colC = st.columns([1, 2, 1])
            with colA:
                if st.button("⬅️ Prev", key=f"{tab_name}_prev"):
                    st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
            with colC:
                if st.button("Next ➡️", key=f"{tab_name}_next"):
                    st.session_state[index_key] = min(len(subset) - 1, st.session_state[index_key] + 1)

            example = subset[st.session_state[index_key]]
            current_index = st.session_state[index_key]

            st.markdown("---")
            st.markdown(f"🧾 **ID:** `{example.get('id', 'unknown')}` → `{example.get('clean_id')}` ({current_index+1}/{len(subset)})")
            for j, p in enumerate(example.get("premises", [])):
                st.markdown(f"**Premise {j+1}:** {p}")
            st.markdown(f"**🔮 Hypothesis:** {example.get('hypothesis', 'unknown')}")

            st.markdown("#### 🧠 Model votes:")
            for model, vote in example.get("model_votes", {}).items():
                st.markdown(f"- `{model}` → **{vote}**")

            with st.expander("✏️ Chỉnh nhãn thủ công (nếu cần)"):
                key = f"{tab_name}_{example['clean_id']}_override"
                override = st.selectbox(
                    "Chọn nhãn mới:",
                    ["", "entailment", "contradiction", "neutral", "implicature"],
                    key=key,
                )
                if override:
                    edited_examples[example["clean_id"]] = override

            auto_label = example.get("auto_label")
            current_label = edited_examples.get(example["clean_id"], example["label"])
            final_note = (
                " (no auto-assigned label)" if auto_label is None
                else " (auto-assigned)" if current_label == auto_label
                else " (overridden manually)"
            )

            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**🔖 Original label:** `{example.get('original_label', 'N/A')}`")
            col2.markdown(f"**🤖 Auto-assigned:** `{auto_label if auto_label else 'None'}`")
            col3.markdown(f"**👤 Final label:** `{current_label}`{final_note}")
