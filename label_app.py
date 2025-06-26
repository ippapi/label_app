import streamlit as st
import json
import math

st.set_page_config(page_title="NLI Labeling Tool", layout="wide")
st.title("🧠 NLI JSON Labeling Tool")

uploaded_file = st.file_uploader("📤 Upload a JSON file", type="json")

if uploaded_file:
    data = json.load(uploaded_file)

    for key in ["assign_type", "final_label", "auto_label", "agreement", "id", "edited_premises", "edited_hypothesis"]:
        if key not in st.session_state:
            st.session_state[key] = {}

    for k in ["filter_by_assign_type", "filter_by_agreement", "filter_by_label", "filter_by_id"]:
        if k not in st.session_state:
            st.session_state[k] = ""

    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

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

    new_id = st.sidebar.text_input("🔍 Search by ID (parsed)", value=st.session_state.filter_by_id)
    if new_id != st.session_state.filter_by_id:
        st.session_state.current_page = 1
    st.session_state.filter_by_id = new_id

    new_label = st.sidebar.selectbox(
        "🧠 Auto Label",
        ["", "entailment", "contradiction", "neutral", "implicature"],
        index=["", "entailment", "contradiction", "neutral", "implicature"].index(st.session_state.filter_by_label)
    )
    if new_label != st.session_state.filter_by_label:
        st.session_state.current_page = 1
    st.session_state.filter_by_label = new_label

    new_agree = st.sidebar.selectbox(
        "🤝 Agreement",
        ["", "3/3", "2/3", "1/3"],
        index=["", "3/3", "2/3", "1/3"].index(st.session_state.filter_by_agreement)
    )
    if new_agree != st.session_state.filter_by_agreement:
        st.session_state.current_page = 1
    st.session_state.filter_by_agreement = new_agree

    new_assign = st.sidebar.selectbox(
        "✍️ Assign Type",
        ["", "Auto", "Manual"],
        index=["", "Auto", "Manual"].index(st.session_state.filter_by_assign_type)
    )
    if new_assign != st.session_state.filter_by_assign_type:
        st.session_state.current_page = 1
    st.session_state.filter_by_assign_type = new_assign

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
    per_page = 10
    total_pages = math.ceil(len(filtered_data) / per_page)
    st.markdown(f"🎯 Đã lọc được **{len(filtered_data)}** mẫu phù hợp. Trang hiện tại: **{st.session_state.current_page}/{total_pages}**")

    start_idx = (st.session_state.current_page - 1) * per_page
    end_idx = start_idx + per_page
    page_data = filtered_data[start_idx:end_idx]

    if not page_data:
        st.warning("⚠️ Không có mẫu nào khớp với bộ lọc.")
    else:
        for idx, ex in enumerate(page_data):
            ex_id = ex["id"]
            st.markdown(f"### 🧾 Sample {start_idx + idx + 1}: `{ex_id}`")
            st.markdown(f"**Parsed ID:** `{st.session_state.id[ex_id]}`")

            default_premises = "\n".join(ex.get("premises", []))
            premises_input = st.text_area(f"📌 Premises (multi-line)", value=st.session_state.edited_premises.get(ex_id, default_premises), height=100, key=f"premises_{ex_id}")
            st.session_state.edited_premises[ex_id] = premises_input

            default_hypo = ex.get("hypothesis", "")
            hypo_input = st.text_input("🎯 Hypothesis", value=st.session_state.edited_hypothesis.get(ex_id, default_hypo), key=f"hypo_{ex_id}")
            st.session_state.edited_hypothesis[ex_id] = hypo_input

            st.markdown(f"**Auto label:** `{st.session_state.auto_label[ex_id]}`")
            st.markdown(f"**Agreement:** `{st.session_state.agreement[ex_id]}`")

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
        cols = st.columns(min(total_pages, 10))
        for i in range(total_pages):
            col = cols[i % 10]
            if col.button(f"{i+1}", key=f"page_{i+1}"):
                st.session_state.current_page = i + 1
                st.experimental_rerun()

    # Tải kết quả
    if st.button("📥 Tải xuống kết quả"):
        export = []
        for ex in data:
            ex_id = ex["id"]
            ex["auto_label"] = st.session_state.auto_label.get(ex_id)
            ex["final_label"] = st.session_state.final_label.get(ex_id, ex.get("auto_label"))
            ex["assign_type"] = st.session_state.assign_type.get(ex_id, "Auto")
            ex["agreement"] = st.session_state.agreement.get(ex_id)

            edited_hypo = st.session_state.edited_hypothesis.get(ex_id)
            if edited_hypo is not None:
                ex["hypothesis"] = edited_hypo

            edited_premises = st.session_state.edited_premises.get(ex_id)
            if edited_premises is not None:
                ex["premises"] = [p.strip() for p in edited_premises.strip().split("\n") if p.strip()]

            export.append(ex)

        json_str = json.dumps(export, indent=2, ensure_ascii=False)
        st.download_button("📄 Tải file kết quả", json_str, file_name="labeled_output.json", mime="application/json")
