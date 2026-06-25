import json
from collections import Counter

with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/a167ae3d-c222-47d6-a040-0f7b4e4e9ba1/threads/dbb54347-66bc-4244-8177-bdf441383454/user-data/outputs/predictions.jsonl') as f:
    preds = [json.loads(line) for line in f if line.strip()]

with open('E:/Demo of GVIM/deer-flow-mainnew/deer-flow-main/.deer-flow/users/a167ae3d-c222-47d6-a040-0f7b4e4e9ba1/threads/dbb54347-66bc-4244-8177-bdf441383454/user-data/uploads/chemu_ner_input.jsonl') as f:
    docs_raw = [json.loads(line) for line in f if line.strip()]
docs = {d['doc_id']: d['text'] for d in docs_raw}

label_counts = Counter()
total_ents = 0
errors = []

for doc in preds:
    doc_id = doc['doc_id']
    text = docs[doc_id]
    for ent in doc['entities']:
        total_ents += 1
        label_counts[ent['label']] += 1
        span = text[ent['start']:ent['end']]
        if span != ent['text']:
            errors.append(f'{doc_id} label={ent["label"]} offset={ent["start"]}:{ent["end"]} expected={repr(ent["text"])} got={repr(span)}')

print(f'Total entities: {total_ents}')
print(f'Label counts:')
for label, cnt in sorted(label_counts.items()):
    print(f'  {label}: {cnt}')
print()
if errors:
    print(f'Errors ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
else:
    print('All spans match perfectly - no errors!')
print()
print(f'Documents: {len(preds)}')
for doc in preds:
    print(f'  {doc["doc_id"]}: {len(doc["entities"])} entities')
