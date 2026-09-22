from pathlib import Path
from ollama import chat


question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""

selected_files = [
    ## Use only the files that are relevant to the question.
    "knowledge/wifi_setup.txt",
    "knowledge/password_changes.txt",
    "knowledge/service_status.txt",
]


context = ""

## Write a for loop to go through all the files in selected_files and read their contents into the context variable.
for file_path in selected_files:
    context += Path(file_path).read_text()
    context += "\n\n"

## Call Qwen with the student's question and the context you created above.
response = chat(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a university IT support assistant. "
                "Use only the provided context to answer the student's question. "
                "Give a clear, step-by-step answer."
            ),
        },
        {
            "role": "user",
            "content": f"Student question:\n{question}\n\nContext:\n{context}",
        },
    ],
)

print(
    "Context characters:",
    len(context)
)
print(response.message.content)