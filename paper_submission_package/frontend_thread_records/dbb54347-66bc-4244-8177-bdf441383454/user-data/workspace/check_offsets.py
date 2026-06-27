import json

with open("E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/a167ae3d-c222-47d6-a040-0f7b4e4e9ba1/threads/dbb54347-66bc-4244-8177-bdf441383454/user-data/uploads/chemu_ner_input.jsonl") as f:
    docs = [json.loads(line) for line in f if line.strip()]

for d in docs:
    text = d["text"]
    doc_id = d["doc_id"]
    print(f"=== {doc_id} ===\n")
    
    # Show full text with character positions every 20 chars for visibility
    for i in range(0, len(text), 80):
        chunk = text[i:i+80]
        line = ""
        for j, ch in enumerate(chunk):
            abs_pos = i + j
            if ch == '\n':
                line += '\\n'
            else:
                line += ch
        print(f"{i:4d}: {line}")
    print("\n\n")
