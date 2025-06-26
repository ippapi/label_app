import streamlit as st
import json

st.set_page_config(page_title="NLI Labeling Tool", layout="wide")
st.title("🧠 NLI JSON Labeling Tool")

uploaded_file = st.file_uploader("📤 Upload a JSON file", type="json")

if uploaded_file:
    data = json.load(uploaded_file)

    # 🧠 Init session state
    for key in ["assign_type", "final_label", "auto_label", "agreement", "id"]:
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

    # Tính auto_label, agreement, parsed_id
    for ex in data:
        ex_id = ex["id"]
        parsed = parse_id(ex_id)
        st.session_state.id[ex_id] = parsed
        st.session_state.auto_label[ex_id] = compute_auto_label(ex)
        st.session_state.agreement[ex_id] = compute_agreement(ex)

    # --- UI filter ---
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

    # --- Filter Data ---
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

    # --- Hiển thị và gán nhãn ---
    if not filtered_data:
        st.warning("⚠️ Không có mẫu nào khớp với bộ lọc.")
    else:
        selected = st.number_input("🔢 Chọn mẫu", 0, len(filtered_data)-1, 0)
        ex = filtered_data[selected]
        ex_id = ex["id"]

        st.markdown(f"**ID**: `{ex_id}`")
        st.markdown(f"**Parsed ID**: `{st.session_state.id[ex_id]}`")

        # ✅ Hiển thị Premises (list)
        st.markdown("**Premises:**")
        if isinstance(ex.get("premises"), list):
            for i, p in enumerate(ex["premises"], 1):
                st.markdown(f"- {i}. {p}")
        else:
            st.markdown(f"- {ex.get('premise', '(Không có premise)')}")

        st.markdown(f"**Hypothesis:** {ex['hypothesis']}")
        st.markdown(f"**Auto label:** `{st.session_state.auto_label[ex_id]}`")
        st.markdown(f"**Agreement:** `{st.session_state.agreement[ex_id]}`")

        label = st.radio("🎯 Gán nhãn thủ công", ["entailment", "contradiction", "neutral", "implicature"],
                         index=["entailment", "contradiction", "neutral", "implicature"].index(
                             st.session_state.final_label.get(ex_id, st.session_state.auto_label[ex_id]) or "entailment"
                         ))

        if st.button("✅ Lưu nhãn"):
            st.session_state.final_label[ex_id] = label
            st.session_state.assign_type[ex_id] = "Manual"
            st.success(f"✅ Đã gán `{label}` cho ID {ex_id}")

    # --- Xuất file ---
    if st.button("📥 Tải xuống kết quả"):
        export = []
        for ex in data:
            ex_id = ex["id"]
            ex["auto_label"] = st.session_state.auto_label.get(ex_id)
            ex["final_label"] = st.session_state.final_label.get(ex_id, ex.get("auto_label"))
            ex["assign_type"] = st.session_state.assign_type.get(ex_id, "Auto")
            ex["agreement"] = st.session_state.agreement.get(ex_id)
            export.append(ex)
        json_str = json.dumps(export, indent=2, ensure_ascii=False)
        st.download_button("📄 Tải file kết quả", json_str, file_name="labeled_output.json", mime="application/json")
