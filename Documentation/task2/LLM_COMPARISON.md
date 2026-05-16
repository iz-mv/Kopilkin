# LLM Model Comparison

The instructor did not require a specific LLM model. The requirement was to compare several lightweight local models that can run on student hardware and justify the final choice. I selected **Ollama** as the local LLM engine and tested three models with the same financial advice prompt.

## Tested prompt

```text
Привет! Я трачу 5000 рублей в месяц на кафе и 3000 на транспорт. Что посоветуешь?
```

## Comparison table

| Criteria | llama3.2:3b | qwen2.5:3b | gemma3:4b |
|---|---|---|---|
| Context understanding | Good general topic understanding | Weak: incorrectly assumed the user owns/manages a cafe | Good: understood personal expenses |
| Russian language quality | Weak: mixed Russian, English, and unstable fragments | Good Russian, but wrong task interpretation | Good Russian |
| Practical usefulness | Low: too generic and linguistically unstable | Low: advice was partly about business management | High: practical, structured, and relevant |
| Hallucination tendency | Present | Present | Minimal in this test |
| Financial advice quality | Generic | Misleading because of wrong context | Useful and personalized |
| Final result | Not selected | Not selected | Selected |

## Final choice

After testing three lightweight local models through Ollama, I selected **gemma3:4b** as the main model for the Kopilkin multi-agent system. Compared to `llama3.2:3b` and `qwen2.5:3b`, Gemma 3 4B provided the best balance between Russian language quality, context understanding, practical financial advice, and low hallucination tendency. It correctly understood that the user was asking about personal expenses, while `qwen2.5:3b` incorrectly interpreted the user as a cafe owner. `llama3.2:3b` produced mixed-language output, which made it less suitable for a user-facing financial assistant.

## Selection criteria

- Ability to run locally on available hardware.
- Quality of Russian and English responses.
- Ability to understand personal finance context.
- Low hallucination tendency.
- Ability to give structured and useful advice.
- Acceptable speed for a local student demo.
