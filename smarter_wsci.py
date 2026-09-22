from pathlib import Path
from ollama import chat
import json


question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""

## WRITE ##
service_status = {
    "wifi": "operational"
}

state = {
    "problem": question,
    "wi_fi_status": "operational",
    "wi_fi_check": True
}

with open("state.json", "w") as file:
    json.dump(state, file, indent=2)

with open("state.json", "r") as file:
    state = json.load(file)

print(state)


## SELECT CONTEXT FILES BASED ON QUESTION
## Takes the student's question, looks for keywords, returns a list of relevant files.
def select_context(question):
    question_lower = question.lower()

    keyword_map = {
        "wi-fi":    ["knowledge/wifi_setup.txt"],
        "wifi":     ["knowledge/wifi_setup.txt"],
        "password": ["knowledge/password_changes.txt"],
        "email":    ["knowledge/email_setup.txt"],
        "vpn":      ["knowledge/vpn.txt"],
        "print":    ["knowledge/printing.txt"],
        "printer":  ["knowledge/printing.txt"],
        "projector":["knowledge/classroom_projectors.txt"],
        "display":  ["knowledge/classroom_projectors.txt"],
        "outage":   ["knowledge/service_status.txt"],
        "status":   ["knowledge/service_status.txt"],
        "operational": ["knowledge/service_status.txt"],
    }

    selected = []
    for keyword, files in keyword_map.items():
        if keyword in question_lower:
            for f in files:
                if f not in selected:
                    selected.append(f)

    # 如果一个问题里同时提到多个问题，总是把服务状态带上（判断是不是全校故障）
    status_file = "knowledge/service_status.txt"
    if status_file not in selected:
        selected.append(status_file)

    return selected


selected_files = select_context(question)
print("Selected files:", selected_files)


## READ SELECTED FILES and add their contents to the context variable.
context = ""
for file_path in selected_files:
    context += Path(file_path).read_text()
    context += "\n\n"


## COMPRESS CONTEXT
## Ask Qwen to compress the context so only relevant info remains.
def compress_context(context, question):
    prompt = (
        "You are a context compression assistant. "
        "Given a student's question and a set of IT knowledge base documents, "
        "extract ONLY the information that is relevant to answering the question. "
        "Be concise. Keep concrete steps, commands, and facts. "
        "Drop anything unrelated.\n\n"
        f"Student question:\n{question}\n\n"
        f"Knowledge base documents:\n{context}\n\n"
        "Return the compressed context as plain text."
    )

    response = chat(
        model="qwen2.5:3b",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    return response.message.content


compressed_context = compress_context(context, question)

## Print the length of the compressed context
print("Compressed context characters:", len(compressed_context))


## Now, call Qwen again with the compressed context and the student's question.
## Ensure the model produces a structured output.
response = chat(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a university IT support assistant. "
                "Use ONLY the provided compressed context. "
                "Return your answer as a JSON object with exactly these keys:\n"
                "{\n"
                '  "diagnosis": "short summary of the likely cause",\n'
                '  "steps": ["step 1", "step 2", ...],\n'
                '  "confidence": "LOW | MEDIUM | HIGH"\n'
                "}\n"
                "Return raw JSON only. No markdown, no explanation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Student question:\n{question}\n\n"
                f"Compressed context:\n{compressed_context}"
            ),
        },
    ],
)

print(response.message.content)


## WRITE the above output in an artifact called "state"

def parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


try:
    answer = parse_json_response(response.message.content)
except json.JSONDecodeError:
    answer = {
        "diagnosis": "Could not parse model output",
        "steps": [],
        "confidence": "LOW",
    }


## ISOLATE ##
## Build different state artifacts for different tasks.

diagnostic_context = {
    "problem": question,
    "device": "Windows laptop",
    "wifi_status": "operational",
    "likely_cause": answer.get("diagnosis", ""),
    "confidence": answer.get("confidence", "LOW"),
}

report_context = {
    "total_wifi_cases": 37,
    "resolved_cases": 29,
    "unresolved_cases": 8,
}

state = {
    "diagnostic_context": diagnostic_context,
    "report_context": report_context,
    "answer": answer,
}

with open("state.json", "w", encoding="utf-8") as file:
    json.dump(state, file, indent=2, ensure_ascii=False)

print("\nstate.json written.")


## Update the rest of the code so that it uses the "state" artifact as part of the context.
## For a new question, we only pull in the relevant slices of state instead of the whole artifact.

def answer_with_state(question, state):
    ## Decide which parts of state are relevant.
    relevant = {
        "problem": state["diagnostic_context"]["problem"],
        "wifi_status": state["diagnostic_context"]["wifi_status"],
        "device": state["diagnostic_context"]["device"],
    }

    prompt = (
        "You are a university IT support assistant. "
        "Use the relevant state information below, along with the student's new question, "
        "to provide a short, structured answer in JSON: "
        '{"diagnosis": "...", "steps": ["..."], "confidence": "LOW|MEDIUM|HIGH"}. '
        "Return raw JSON only.\n\n"
        f"Relevant state:\n{json.dumps(relevant, indent=2)}\n\n"
        f"New question:\n{question}"
    )

    resp = chat(
        model="qwen2.5:3b",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.message.content


followup_question = "Should I also update the saved password in my email app?"
print("\nFollow-up answer:")
print(answer_with_state(followup_question, state))