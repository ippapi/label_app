import streamlit as st
import json
import re
from collections import Counter

st.set_page_config(
    page_title="Multihop NLI Label Review",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
with st.sidebar:
    st.title("📂 File dữ liệu")
    uploaded_file = st.file_uploader("📤 Tải file JSON", type=["json"])
    export_filename = st.text_input("💾 Tên file xuất (.json)", value="updated_labeled.json")
    export_trigger = st.button("📥 Tải xuống file kết quả")

# Main
if uploaded_file:
    data = json.load(uploaded_file)

    st.session_state.setdefault("edited_premises", {})
    st.session_state.setdefault("edited_hypothesis", {})
    st.session_state.setdefault("edit_history", {})

    edited_examples = {}

    # Xử lý từng mẫu
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

    # Tabs
    tab_groups = {
        "🧠 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "✍️ Manually assigned": [ex for ex in data if ex["override_type"] == "manual"
                                 and ex["auto_label"] is not None and ex["label"] != ex["auto_label"]],
        "✅ 3/3 models agree": [ex for ex in data if ex["num_agree"] == 3],
        "⚠️ 2/3 models agree": [ex for ex in data if ex["num_agree"] == 2],
        "❌ 1/3 or all different": [ex for ex in data if ex["num_agree"] <= 1],
        "🟩 entailment": [ex for ex in data if ex["label"] == "entailment"],
        "🟥 contradiction": [ex for ex in data if ex["label"] == "contradiction"],
        "🟨 neutral": [ex for ex in data if ex["label"] == "neutral"],
        "🟦 implicature": [ex for ex in data if ex["label"] == "implicature"],
    }

    tab_names = list(tab_groups.keys())
    tabs = st.tabs(tab_names)

    for i, tab_name in enumerate(tab_names):
        subset = tab_groups[tab_name]
        with tabs[i]:
            st.markdown(f"### 📊 Số lượng mẫu: {len(subset)}")

            index_key = f"{tab_name}_index"
            st.session_state.setdefault(index_key, 0)

            col1, col2, col3 = st.columns([4, 3, 3])
            with col1:
                search_id = st.text_input("🔎 Tìm theo ID", key=f"{tab_name}_search_id")
            with col2:
                max_page = max(1, len(subset))
                default_goto = min(st.session_state.get(f"{tab_name}_goto_index", 1), max_page)
                goto_page = st.number_input("🔢 Đi đến vị trí", 1, max_page, default_goto, key=f"{tab_name}_goto_index")
            with col3:
                if st.button("🚀 Tìm / Chuyển trang", key=f"{tab_name}_search_btn"):
                    found = False
                    if search_id:
                        for idx, ex in enumerate(subset):
                            if ex["clean_id"] == search_id:
                                st.session_state[index_key] = idx
                                st.success(f"🔍 Tìm thấy ID `{search_id}` ở vị trí {idx+1}/{len(subset)}")
                                found = True
                                break
                        if not found:
                            st.warning(f"⚠️ Không tìm thấy ID `{search_id}`.")
                    else:
                        st.session_state[index_key] = int(goto_page) - 1

            if not subset:
                st.info("Không có mẫu nào trong tab này.")
                continue

            nav_left, main_col, nav_right = st.columns([1, 10, 1])
            with nav_left:
                if st.button("◀️", key=f"{tab_name}_prev"):
                    st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
            with nav_right:
                if st.button("▶️", key=f"{tab_name}_next"):
                    st.session_state[index_key] = min(len(subset) - 1, st.session_state[index_key] + 1)

            current_index = st.session_state[index_key]
            example = subset[current_index]

            with main_col:
                st.markdown("---")
                st.markdown(f"🧾 **ID:** `{example['id']}` → `{example['clean_id']}` ({current_index+1}/{len(subset)})")

                # === Premises ===
                st.markdown("#### 🧱 Premises:")
                updated_premises = []
                for j, p in enumerate(example.get("premises", [])):
                    hist_key = f"{example['clean_id']}_premise_{j}"
                    st.session_state["edit_history"].setdefault(hist_key, {"history": [p], "index": 0})
                    hist = st.session_state["edit_history"][hist_key]
                    current_val = hist["history"][hist["index"]]
                    ta_key = f"{tab_name}_{hist_key}"

                    c1, c2, c3, c4, c5 = st.columns([6, 1, 1, 1, 1])
                    with c1:
                        st.markdown(f"**Premise {j+1}:**")
                    with c2:
                        if st.button("🔄", help="Reset", key=f"{ta_key}_reset"):
                            hist["history"].append(p)
                            hist["index"] = len(hist["history"]) - 1
                    with c3:
                        if st.button("↩️", help="Undo", key=f"{ta_key}_undo") and hist["index"] > 0:
                            hist["index"] -= 1
                    with c4:
                        if st.button("↪️", help="Redo", key=f"{ta_key}_redo") and hist["index"] < len(hist["history"]) - 1:
                            hist["index"] += 1

                    new_val = st.text_area("", value=hist["history"][hist["index"]],
                                           key=ta_key, height=60, label_visibility="collapsed")

                    if new_val != hist["history"][hist["index"]]:
                        hist["history"] = hist["history"][:hist["index"] + 1] + [new_val]
                        hist["index"] += 1

                    updated_premises.append(hist["history"][hist["index"]])
                st.session_state["edited_premises"][example["clean_id"]] = updated_premises

                # === Hypothesis ===
                st.markdown("#### 🔮 Hypothesis:")
                hyp_key = f"{example['clean_id']}_hypothesis"
                original_hyp = example.get("hypothesis", "")
                st.session_state["edit_history"].setdefault(hyp_key, {"history": [original_hyp], "index": 0})
                hist = st.session_state["edit_history"][hyp_key]
                ta_key = f"{tab_name}_{hyp_key}"

                c1, c2, c3, c4, c5 = st.columns([6, 1, 1, 1, 1])
                with c1:
                    st.markdown("**Hypothesis:**")
                with c2:
                    if st.button("🔄", help="Reset", key=f"{ta_key}_reset"):
                        hist["history"].append(original_hyp)
                        hist["index"] = len(hist["history"]) - 1
                with c3:
                    if st.button("↩️", help="Undo", key=f"{ta_key}_undo") and hist["index"] > 0:
                        hist["index"] -= 1
                with c4:
                    if st.button("↪️", help="Redo", key=f"{ta_key}_redo") and hist["index"] < len(hist["history"]) - 1:
                        hist["index"] += 1

                edited_val = st.text_area("", value=hist["history"][hist["index"]],
                                          key=ta_key, height=80, label_visibility="collapsed")

                if edited_val != hist["history"][hist["index"]]:
                    hist["history"] = hist["history"][:hist["index"] + 1] + [edited_val]
                    hist["index"] += 1
                st.session_state["edited_hypothesis"][example["clean_id"]] = hist["history"][hist["index"]]

                # Model votes
                st.markdown("#### 🧠 Model votes:")
                for model, vote in example.get("model_votes", {}).items():
                    st.markdown(f"- `{model}` → **{vote}**")

                # Label override
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

    # Export JSON
    if export_trigger:
        for example in data:
            cid = example["clean_id"]
            if cid in edited_examples:
                example["label"] = edited_examples[cid]
                example["override_type"] = "manual" if example["label"] != example["auto_label"] else "auto"
            if cid in st.session_state["edited_premises"]:
                example["premises"] = st.session_state["edited_premises"][cid]
            if cid in st.session_state["edited_hypothesis"]:
                example["hypothesis"] = st.session_state["edited_hypothesis"][cid]

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("📥 Click để tải JSON", data=json_str.encode("utf-8"),
                           file_name=export_filename, mime="application/json")
else:
    st.info("📥 Vui lòng tải file JSON từ sidebar để bắt đầu.")
