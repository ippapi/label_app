import streamlit as st
import json
import math

st.set_page_config(page_title="NLI Labeling Tool", layout="wide")
st.title("🧠 NLI JSON Labeling Tool")

uploaded_file = st.file_uploader("📤 Upload a JSON file", type="json")

if uploaded_file:
    data = json.load(uploaded_file)

    # Init session state
    for key in ["assign_type", "final_label", "auto_label", "agreement", "id", "edited_premises", "edited_hypothesis"]:
        if key not in st.session_state:
            st.session_state[key] = {}

    for k in ["filter_by_assign_type", "filter_by_agreement", "filter_by_label", "filter_by_id"]:
        if k not in st.session_state:
            st.session_state[k] = ""

    def parse_id(example_id):
        try:
            return example_id.split("_")[-2] + "_" + example_id.split("_")[-1]
        except:
            return example_id

    def compute_auto_label(example):
        validated_fields = {k: v for k, v in example.items() if k.endswith("_validated")}
        label_counts = {}
        for label in validated_fields.values():
            label_counts[label] = label_counts.get(label, 0) + 1
        if len(set(label_counts.values())) == 1 and len(label_counts) == 3:
            return None
        max_count = max(label_counts.values())
        top_labels = [k for k, v in label_counts.items() if v == max_count]
        return top_labels[0] if len(top_labels) == 1 else None

    def compute_agreement(example):
        labels = [v for k, v in example.items() if k.endswith("_validated")]
        counter = {l: labels.count(l) for l in set(labels)}
        counts = list(counter.values())
        if 3 in counts:
            return "3/3"
        elif 2 in counts:
            return "2/3"
        return "1/3"

    for ex in data:
        ex_id = ex["id"]
        st.session_state.id[ex_id] = parse_id(ex_id)
        st.session_state.auto_label[ex_id] = compute_auto_label(ex)
        st.session_state.agreement[ex_id] = compute_agreement(ex)

    # Bộ lọc
    st.sidebar.header("🎛️ Bộ lọc")

    st.session_state.filter_by_id = st.sidebar.text_input("🔍 Search by ID (parsed)", value=st.session_state.filter_by_id)

    st.session_state.filter_by_label = st.sidebar.selectbox(
        "🧠 Auto Label",
        ["", "entailment", "contradiction", "neutral", "implicature"],
        index=["", "entailment", "contradiction", "neutral", "implicature"].index(st.session_state.filter_by_label)
    )

    st.session_state.filter_by_agreement = st.sidebar.selectbox(
        "🤝 Agreement",
        ["", "3/3", "2/3", "1/3"],
        index=["", "3/3", "2/3", "1/3"].index(st.session_state.filter_by_agreement)
    )

    st.session_state.filter_by_assign_type = st.sidebar.selectbox(
        "✍️ Assign Type",
        ["", "Auto", "Manual"],
        index=["", "Auto", "Manual"].index(st.session_state.filter_by_assign_type)
    )

    # Lọc dữ liệu
    filtered_data = []
    for ex in data:
        ex_id = ex["id"]
        if st.session_state.filter_by_id and st.session_state.filter_by_id.lower() not in st.session_state.id[ex_id].lower():
            continue
        if st.session_state.filter_by_label and st.session_state.auto_label[ex_id] != st.session_state.filter_by_label:
            continue
        if st.session_state.filter_by_agreement and st.session_state.agreement[ex_id] != st.session_state.filter_by_agreement:
            continue
        if st.session_state.filter_by_assign_type:
            assign_type = st.session_state.assign_type.get(ex_id, "Auto")
            if assign_type != st.session_state.filter_by_assign_type:
                continue
        filtered_data.append(ex)

    # Phân trang
    per_page = 5
    total_pages = math.ceil(len(filtered_data) / per_page)
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    current_page = st.session_state.current_page

    st.markdown(f"🎯 Đã lọc được **{len(filtered_data)}** mẫu phù hợp. Trang hiện tại: **{current_page}/{total_pages}**")

    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page
    page_data = filtered_data[start_idx:end_idx]

    if not page_data:
        st.warning("⚠️ Không có mẫu nào khớp với bộ lọc.")
    else:
        for idx, ex in enumerate(page_data):
            ex_id = ex["id"]
            st.markdown(f"### 🧾 Sample {start_idx + idx + 1}: `{ex_id}`")
            st.markdown(f"**Parsed ID:** `{st.session_state.id[ex_id]}`")

            # --- Premises: mỗi dòng 1 input ---
            edited_premises = st.session_state.edited_premises.get(ex_id, ex.get("premises", []))
            if not isinstance(edited_premises, list):
                edited_premises = [p.strip() for p in edited_premises.strip().split("\n") if p.strip()]
            st.session_state.edited_premises[ex_id] = edited_premises

            new_premises = []
            st.markdown("📌 **Premises**:")
            for i, p in enumerate(edited_premises or [""]):
                updated = st.text_input(f"Premise {i+1}", value=p, key=f"{ex_id}_premise_{i}")
                new_premises.append(updated)
            if st.button(f"➕ Thêm premise", key=f"add_premise_{ex_id}"):
                new_premises.append("")
            st.session_state.edited_premises[ex_id] = new_premises

            # --- Hypothesis ---
            default_hypo = ex.get("hypothesis", "")
            hypo_input = st.text_input("🎯 Hypothesis", value=st.session_state.edited_hypothesis.get(ex_id, default_hypo), key=f"hypo_{ex_id}")
            st.session_state.edited_hypothesis[ex_id] = hypo_input

            st.markdown(f"**Auto label:** `{st.session_state.auto_label[ex_id]}`")
            st.markdown(f"**Agreement:** `{st.session_state.agreement[ex_id]}`")
            st.markdown("**🧠 Các nhãn từ mô hình:**")
            model_labels = {k: v for k, v in ex.items() if k.endswith("_validated")}
            if model_labels:
                for model_name, label_val in model_labels.items():
                    st.markdown(f"- `{model_name}`: **{label_val}**")
            else:
                st.info("Không có nhãn mô hình.")


            label = st.radio("🏷️ Gán nhãn", ["entailment", "contradiction", "neutral", "implicature"],
                             index=["entailment", "contradiction", "neutral", "implicature"].index(
                                 st.session_state.final_label.get(ex_id, st.session_state.auto_label[ex_id]) or "entailment"
                             ), horizontal=True, key=f"label_{ex_id}")

            if st.button("✅ Lưu nhãn", key=f"save_{ex_id}"):
                st.session_state.final_label[ex_id] = label
                st.session_state.assign_type[ex_id] = "Manual"
                st.success(f"Gán `{label}` cho ID {ex_id} thành công!")

        # Điều hướng trang
        st.divider()
        nav_cols = st.columns(9)

        def change_page(new_page):
            st.session_state.current_page = new_page
            st.experimental_rerun()

        if current_page > 1:
            if nav_cols[0].button("«"):
                change_page(current_page - 1)
        else:
            nav_cols[0].write("")

        max_buttons = 7
        half = max_buttons // 2
        start = max(1, current_page - half)
        end = min(total_pages, start + max_buttons - 1)
        if end - start < max_buttons:
            start = max(1, end - max_buttons + 1)

        for i, page_num in enumerate(range(start, end + 1)):
            if page_num == current_page:
                nav_cols[i + 1].markdown(
                    f"<div style='height: 38px; line-height: 38px; width: 36px;  text-align: center; ; border-radius: 6px; background-color: rgb(0, 102, 204); color: white; font-weight: bold;'>{page_num}</div>",
                    unsafe_allow_html=True
                )
            else:
                if nav_cols[i + 1].button(f"{page_num}", key=f"pg_{page_num}"):
                    change_page(page_num)

        if current_page < total_pages:
            if nav_cols[8].button("»"):
                change_page(current_page + 1)
        else:
            nav_cols[8].write("")

    # Xuất file
    if st.button("📥 Tải xuống kết quả"):
        export = []
        for ex in data:
            ex_id = ex["id"]
            ex["auto_label"] = st.session_state.auto_label.get(ex_id)
            ex["final_label"] = st.session_state.final_label.get(ex_id, ex.get("auto_label"))
            ex["assign_type"] = st.session_state.assign_type.get(ex_id, "Auto")
            ex["agreement"] = st.session_state.agreement.get(ex_id)

            # Update văn bản
            edited_hypo = st.session_state.edited_hypothesis.get(ex_id)
            if edited_hypo is not None:
                ex["hypothesis"] = edited_hypo

            edited_premises = st.session_state.edited_premises.get(ex_id)
            if edited_premises is not None:
                ex["premises"] = [p.strip() for p in edited_premises if p.strip()]

            export.append(ex)

        json_str = json.dumps(export, indent=2, ensure_ascii=False)
        st.download_button("📄 Tải file kết quả", json_str, file_name="labeled_output.json", mime="application/json")
