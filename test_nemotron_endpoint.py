import os

from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

stream = client.chat.completions.create(
    model="nvidia/nemotron-3-nano-30b-a3b",
    messages=[
        {
            "role": "user",
            "content": "Give me 3 bullet ideas for a RAG hackathon demo.",
        }
    ],
    temperature=0.7,
    top_p=1.0,
    max_tokens=1024,
    extra_body={
        "reasoning_budget": 1024,
        "chat_template_kwargs": {"enable_thinking": True},
    },
    stream=True,
)

for chunk in stream:
    # Some streamed chunks can be empty/metadata
    if not getattr(chunk, "choices", None):
        continue
    if len(chunk.choices) == 0:
        continue

    delta = chunk.choices[0].delta

    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning:
        print(reasoning, end="")

    content = getattr(delta, "content", None)
    if content:
        print(content, end="")
