import streamlit as st
import json

st.set_page_config(page_title="JSON Labeling Tool", layout="wide")
st.title("🧠 JSON Labeling Tool with Filter")

# Upload file
uploaded_file = st.file_uploader("📤 Upload a JSON file", type="json")

if uploaded_file:
    raw_data = json.load(uploaded_file)

    # Load state
    if "final_labels" not in st.session_state:
        st.session_state.final_labels = {}
    if "filter_option" not in st.session_state:
        st.session_state.filter_option = "Chưa gán"

    # Select filter
    filter_option = st.selectbox(
        "📊 Filter samples by label status:",
        ["Tất cả", "Đã gán", "Chưa gán"],
        index=["Tất cả", "Đã gán", "Chưa gán"].index(st.session_state.filter_option)
    )
    st.session_state.filter_option = filter_option

    # Apply filter
    def is_labeled(item):
        return item["id"] in st.session_state.final_labels

    if filter_option == "Tất cả":
        filtered_data = raw_data
    elif filter_option == "Đã gán":
        filtered_data = [item for item in raw_data if is_labeled(item)]
    else:  # Chưa gán
        filtered_data = [item for item in raw_data if not is_labeled(item)]

    if not filtered_data:
        st.info("Không có mẫu nào phù hợp với bộ lọc.")
    else:
        # Select sample
        selected_idx = st.number_input(
            f"🧾 Chọn mẫu (0 đến {len(filtered_data) - 1})", min_value=0, max_value=len(filtered_data) - 1, step=1
        )
        current_item = filtered_data[selected_idx]
        item_id = current_item["id"]

        st.subheader(f"Mẫu ID: {item_id}")
        st.markdown(f"**Premise:** {current_item['premise']}")
        st.markdown(f"**Hypothesis:** {current_item['hypothesis']}")

        current_label = st.session_state.final_labels.get(item_id, None)

        label = st.radio(
            "🎯 Gán nhãn:",
            ["entailment", "neutral", "contradiction"],
            index=["entailment", "neutral", "contradiction"].index(current_label) if current_label else 0
        )

        if st.button("💾 Lưu nhãn"):
            st.session_state.final_labels[item_id] = label
            st.success(f"✅ Đã lưu nhãn cho ID {item_id}: {label}")

        # Xem kết quả
        st.markdown("---")
        if st.checkbox("📋 Xem toàn bộ nhãn đã gán"):
            labeled_items = [
                {
                    **item,
                    "final_label": st.session_state.final_labels[item["id"]]
                }
                for item in raw_data
                if item["id"] in st.session_state.final_labels
            ]
            st.json(labeled_items)

        # Xuất file kết quả
        if st.button("📥 Tải xuống file JSON đã gán nhãn"):
            result = []
            for item in raw_data:
                item_copy = item.copy()
                item_copy["final_label"] = st.session_state.final_labels.get(item["id"], "")
                result.append(item_copy)
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Tải file kết quả",
                data=json_str,
                file_name="labeled_data.json",
                mime="application/json"
            )
