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
    st.title("\U0001F4C2 File dữ liệu")
    uploaded_file = st.file_uploader("\U0001F4E4 Tải file JSON", type=["json"])
    export_filename = st.text_input("\U0001F4BE Tên file xuất (.json)", value="updated_labeled.json")

if uploaded_file:
    data = json.load(uploaded_file)
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

        example["label"] = example.get("label", "")
        example["override_type"] = "auto" if auto_label else "manual"
        example["original_label"] = example.get("original_label", example.get("label", "unknown"))
        example["auto_label"] = auto_label
        example["num_agree"] = num_agree
        example["model_votes"] = model_votes

    tab_groups = {
        "\U0001F9E0 Auto-assigned": [ex for ex in data if ex["override_type"] == "auto"],
        "\u270D\ufe0f Manually assigned": [ex for ex in data if ex["override_type"] == "manual"
                                     and ex["auto_label"] is not None and ex["label"] != ex["auto_label"]],
        "\u2705 3/3 models agree": [ex for ex in data if ex["num_agree"] == 3],
        "\u26A0\ufe0f 2/3 models agree": [ex for ex in data if ex["num_agree"] == 2],
        "❌ 1/3 or all different": [ex for ex in data if ex["num_agree"] <= 1],
        "\U0001F7E9 entailment": [ex for ex in data if ex["label"] == "entailment"],
        "\U0001F7E5 contradiction": [ex for ex in data if ex["label"] == "contradiction"],
        "\U0001F7E8 neutral": [ex for ex in data if ex["label"] == "neutral"],
        "\U0001F7E6 implicature": [ex for ex in data if ex["label"] == "implicature"],
    }

    tab_names = list(tab_groups.keys())
    tabs = st.tabs(tab_names)

    for i, tab_name in enumerate(tab_names):
        subset = tab_groups[tab_name]
        with tabs[i]:
            st.markdown(f"### \U0001F4CA Số lượng mẫu: {len(subset)}")
            index_key = f"{tab_name}_index"
            st.session_state.setdefault(index_key, 0)

            col1, col2, col3 = st.columns([4, 3, 3])
            with col1:
                search_id = st.text_input("\U0001F50E Tìm theo ID", key=f"{tab_name}_search_id")
            with col2:
                max_page = max(1, len(subset))
                default_goto = min(st.session_state.get(f"{tab_name}_goto_index", 1), max_page)
                goto_page = st.number_input("\U0001F522 Đi đến vị trí", 1, max_page, default_goto, key=f"{tab_name}_goto_index")
            with col3:
                if st.button("\U0001F680 Tìm / Chuyển trang", key=f"{tab_name}_search_btn"):
                    found = False
                    if search_id:
                        for idx, ex in enumerate(subset):
                            if ex["clean_id"] == search_id:
                                st.session_state[index_key] = idx
                                st.success(f"\U0001F50D Tìm thấy ID `{search_id}` ở vị trí {idx+1}/{len(subset)}")
                                found = True
                                break
                        if not found:
                            st.warning(f"\u26A0\ufe0f Không tìm thấy ID `{search_id}`.")
                    else:
                        st.session_state[index_key] = int(goto_page) - 1

            if not subset:
                st.info("Không có mẫu nào trong tab này.")
                continue

            nav_left, main_col, nav_right = st.columns([1, 10, 1])
            with nav_left:
                if st.button("\u25C0\ufe0f", key=f"{tab_name}_prev"):
                    st.session_state[index_key] = max(0, st.session_state[index_key] - 1)
            with nav_right:
                if st.button("\u25B6\ufe0f", key=f"{tab_name}_next"):
                    st.session_state[index_key] = min(len(subset) - 1, st.session_state[index_key] + 1)

            current_index = st.session_state[index_key]
            example = subset[current_index]

            with main_col:
                st.markdown("---")
                st.markdown(f"\U0001F9FE **ID:** `{example['id']}` → `{example['clean_id']}` ({current_index+1}/{len(subset)})")

                updated_premises = []
                for j, p in enumerate(example.get("premises", [])):
                    field_key = f"{tab_name}_{example['clean_id']}_premise_{j}"
                    edit_text_simple(f"Premise {j+1}:", field_key, p, height=80)
                    updated_premises.append(st.session_state[field_key])
                example["premises"] = updated_premises

                hyp_key = f"{tab_name}_{example['clean_id']}_hypothesis"
                original_hyp = example.get("hypothesis", "")
                edit_text_simple("Hypothesis:", hyp_key, original_hyp, height=100)
                example["hypothesis"] = st.session_state[hyp_key]

                st.markdown("#### \U0001F9E0 Model votes:")
                for model, vote in example.get("model_votes", {}).items():
                    st.markdown(f"- `{model}` → **{vote}**")

                with st.expander("\u270D\ufe0f Chỉnh nhãn thủ công"):
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
                col1.markdown(f"**\U0001F516 Original label:** `{example.get('label', 'N/A')}`")
                col2.markdown(f"**\U0001F916 Auto-assigned:** `{auto_label or 'None'}`")
                col3.markdown(f"**\U0001F464 Final label:** `{current_label}`{final_note}")

    with st.sidebar:
        for example in data:
            clean_id = example["clean_id"]
            final = st.session_state["edited_label"].get(clean_id, example.get("auto_label") or example.get("label"))
            example["final_label"] = final

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button("\U0001F4E5 Tải file kết quả", data=json_str.encode("utf-8"),
                           file_name=export_filename, mime="application/json")

    time.sleep(60)
    st.rerun()
else:
    st.info("\U0001F4E5 Vui lòng tải file JSON từ sidebar để bắt đầu.")
