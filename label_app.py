import gradio as gr
import json

with open("example.json", "r", encoding="utf-8") as f:
    data = json.load(f)

example_ids = [ex["id"] for ex in data]

state = {
    "current": 0,
    "edited_premises": {},
    "edited_hypothesis": {},
    "edited_label": {}
}

def get_example(index):
    ex = data[index]
    return ex["id"], "\n\n".join(ex["premises"]), ex["hypothesis"], ex.get("label", ""), ex.get("auto_label", "")

def save_example(index, premises, hypothesis, label):
    clean_id = data[index]["id"]
    state["edited_premises"][clean_id] = premises.strip().split("\n\n")
    state["edited_hypothesis"][clean_id] = hypothesis
    state["edited_label"][clean_id] = label
    return "✅ Đã lưu!"

def go_next():
    state["current"] = min(state["current"] + 1, len(data) - 1)
    return get_example(state["current"])

def go_prev():
    state["current"] = max(state["current"] - 1, 0)
    return get_example(state["current"])

def download():
    for ex in data:
        cid = ex["id"]
        ex["final_label"] = state["edited_label"].get(cid, ex.get("auto_label", ex.get("label", "")))
        if cid in state["edited_premises"]:
            ex["premises"] = state["edited_premises"][cid]
        if cid in state["edited_hypothesis"]:
            ex["hypothesis"] = state["edited_hypothesis"][cid]
    return json.dumps(data, indent=2, ensure_ascii=False)

with gr.Blocks() as demo:
    gr.Markdown("# 🔍 Multi-hop NLI Labeling")

    with gr.Row():
        prev_btn = gr.Button("◀️ Prev")
        next_btn = gr.Button("Next ▶️")
        download_btn = gr.Button("💾 Export JSON")
        save_msg = gr.Textbox(label="", interactive=False)

    ex_id = gr.Textbox(label="ID", interactive=False)
    premises = gr.Textbox(lines=6, label="Premises", placeholder="Premise1\n\nPremise2")
    hypothesis = gr.Textbox(lines=2, label="Hypothesis")
    label = gr.Dropdown(["entailment", "contradiction", "neutral", "implicature", ""], label="Final Label")
    auto_label = gr.Textbox(label="Auto Label", interactive=False)

    prev_btn.click(go_prev, outputs=[ex_id, premises, hypothesis, label, auto_label])
    next_btn.click(go_next, outputs=[ex_id, premises, hypothesis, label, auto_label])
    premises.change(lambda x: "", premises, save_msg)  # reset msg
    save_btn = gr.Button("💾 Save")
    save_btn.click(save_example, inputs=[lambda: state["current"], premises, hypothesis, label], outputs=save_msg)
    download_btn.click(download, outputs=gr.File(label="Download"))

    demo.load(fn=lambda: get_example(state["current"]), outputs=[ex_id, premises, hypothesis, label, auto_label])
