import openai

# Ensure you have your API key set up correctly
openai_client = openai.OpenAI(api_key="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")  # Use dotenv or env variables for security

response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello, how do I fix SQL Injection?"}]
)

print(response.choices[0].message.content)
