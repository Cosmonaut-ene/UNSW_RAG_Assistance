import openai

client = openai.OpenAI(api_key="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")

response = client.chat.completions.create(
    model="gpt-4o",  # 或 gpt-3.5-turbo
    messages=[
        {"role": "user", "content": "Hello!"},
    ]
)

print(response.choices[0].message.content)
