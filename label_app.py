# multihop_nli_label_tool.py
import streamlit as st
import json
import re
from collections import Counter

def edit_text_with_history(label: str, key_prefix: str, original_text: str, height=80):
    key = key_prefix
    reset_key = key + "_reset"
    undo_key = key + "_undo"
    redo_key = key + "_redo"

    st.session_state.setdefault("edit_history", {})
    st.session_state["edit_history"].setdefault(key, {"history": [original_text], "index": 0})
    hist = st.session_state["edit_history"][key]

    for k in [reset_key, undo_key, redo_key]:
        st.session_state.setdefault(k, False)

    c1, c2, c3, c4, c5 = st.columns([6, 1, 1, 1, 1])
    with c1:
        st.markdown(f"**{label}**")
    with c2:
        if st.button("🔄", help="Reset", key=reset_key + "_btn"):
            st.session_state[reset_key] = True
    with c3:
        if st.button("↩️", help="Undo", key=undo_key + "_btn"):
            st.session_state[undo_key] = True
    with c4:
        if st.button("↪️", help="Redo", key=redo_key + "_btn"):
            st.session_state[redo_key] = True

    if st.session_state[reset_key]:
        hist["history"].append(original_text)
        hist["index"] = len(hist["history"]) - 1
        st.session_state[reset_key] = False

    if st.session_state[undo_key] and hist["index"] > 0:
        hist["index"] -= 1
        st.session_state[undo_key] = False

    if st.session_state[redo_key] and hist["index"] < len(hist["history"]) - 1:
        hist["index"] += 1
        st.session_state[redo_key] = False

    new_val = st.text_area(
        "", value=hist["history"][hist["index"]],
        key=key, height=height, label_visibility="collapsed"
    )

    if new_val != hist["history"][hist["index"]]:
        hist["history"] = hist["history"][:hist["index"] + 1] + [new_val]
        hist["index"] += 1

    return hist["history"][hist["index"]]

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

        # ❗ Không thay đổi example["label"]
        example["label"] = example.get("label", "")
        example["override_type"] = "auto" if auto_label else "manual"
        example["original_label"] = example.get("original_label", example.get("label", "unknown"))
        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

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

                updated_premises = []
                for j, p in enumerate(example.get("premises", [])):
                    field_key = f"{example['clean_id']}_premise_{j}"
                    updated_val = edit_text_with_history(f"Premise {j+1}:", f"{tab_name}_{field_key}", p, height=80)
                    updated_premises.append(updated_val)
                st.session_state["edited_premises"][example["clean_id"]] = updated_premises

                hyp_key = f"{example['clean_id']}_hypothesis"
                original_hyp = example.get("hypothesis", "")
                edited_hyp = edit_text_with_history("Hypothesis:", f"{tab_name}_{hyp_key}", original_hyp, height=100)
                st.session_state["edited_hypothesis"][example["clean_id"]] = edited_hyp

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
                        st.session_state["edited_label"][example["clean_id"]] = override

                auto_label = example.get("auto_label")
                current_label = st.session_state["edited_label"].get(example["clean_id"], auto_label or example["label"])
                final_note = (
                    " (no auto-assigned)" if auto_label is None
                    else " (auto-assigned)" if current_label == auto_label
                    else " (overridden manually)"
                )

                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**🔖 Original label:** `{example.get('label', 'N/A')}`")
                col2.markdown(f"**🤖 Auto-assigned:** `{auto_label or 'None'}`")
                col3.markdown(f"**👤 Final label:** `{current_label}`{final_note}")

    # ✅ Tải file kết quả từ sidebar + thêm final_label
    with st.sidebar:
        for example in data:
            clean_id = example["clean_id"]
            final = st.session_state["edited_label"].get(clean_id, example.get("auto_label") or example.get("label"))
            example["final_label"] = final

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("📥 Tải file kết quả", data=json_str.encode("utf-8"),
                           file_name=export_filename, mime="application/json")
else:
    st.info("📥 Vui lòng tải file JSON từ sidebar để bắt đầu.")
