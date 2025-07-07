import requests

url = "http://127.0.0.1:5000/api/ask"
data = {
    "question": "What is the Master of Information Technology at UNSW?"
}

response = requests.post(url, json=data)

print("状态码:", response.status_code)
print("返回内容:")
try:
    print(response.json())
except Exception as e:
    print("❌ 无法解析为 JSON:", e)
    print("原始返回:", response.text)
