# Qorvex Pay RAG assistant

Асистент, що відповідає на питання про вигадане платіжне API **Qorvex Pay** (документація в [docs/](docs/)).
Порівнюємо два режими: модель з RAG (пошук по документації) і без нього.

| Частина | Де |
|---|---|
| Документація API | [docs/](docs/) |
| Чанкінг, embeddings, Chroma, `retrieve(query, k)` | [rag/retrieve.py](rag/retrieve.py) |
| LLM через Ollama | [assistant/llm.py](assistant/llm.py) |
| Промпти (RAG і без RAG) | [assistant/prompts.py](assistant/prompts.py) |
| Контракт `answer(question, use_rag) -> str` | [assistant/core.py](assistant/core.py) |
| CLI | [assistant/\_\_main\_\_.py](assistant/__main__.py) |
| Веб-інтерфейс (Streamlit) | [app.py](app.py) |
| Тестові питання з еталонами | [eval/questions.yaml](eval/questions.yaml) |
| Прогін оцінки та таблиця | [eval/run_eval.py](eval/run_eval.py) |

## Встановлення

Потрібні Python 3.13 (у chromadb/onnxruntime ще немає збірок для 3.15) і [Ollama](https://ollama.com).

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3:8b      # ~5 GB, один раз
ollama serve              # якщо Ollama ще не запущена (у застосунку Ollama сервер стартує сам)
```

Іншу модель можна вибрати змінною середовища: `OLLAMA_MODEL=llama3.1:8b`.

## Запуск

```bash
.venv/bin/streamlit run app.py                                      # веб-інтерфейс
.venv/bin/python -m assistant "How long is the refund window?"      # одне питання, RAG
.venv/bin/python -m assistant "..." --no-rag                        # без RAG
.venv/bin/python -m assistant "..." --compare --sources             # обидва режими + знайдені фрагменти
.venv/bin/python -m assistant                                       # інтерактивний режим
```

З коду:

```python
from assistant import answer, ask
answer("How do I verify webhook signatures?", use_rag=True)   # -> str
ask("...", use_rag=True, k=5)   # -> Answer(text, chunks, seconds, ...)
```

## Оцінка

Окремо пошук, без LLM (швидко): для кожного питання — на якій позиції знайдено фрагмент із потрібним фактом (поле `evidence` у questions.yaml), і recall@k.

```bash
.venv/bin/python -m eval.retrieval_eval                   # гібридний пошук (за замовчуванням)
.venv/bin/python -m eval.retrieval_eval --method vector   # лише embeddings, для порівняння
```

Повний прогін з LLM:

```bash
.venv/bin/python -m eval.run_eval              # 15 питань x 2 режими, ~10 хв на M-серії
.venv/bin/python -m eval.run_eval --only q05   # одне питання
```

Результати потрапляють у `eval/results/<дата>/`:
- `results.csv` — відповідь у кожному режимі та автоматичні підказки:
  - `facts_found` — скільки ключових фактів з еталону знайдено у відповіді;
  - `invented` — ендпоінти, заголовки і `ідентифікатори`, яких немає ніде в docs/ (вигадані);
  - `verdict_judge` — чернетка оцінки від LLM (correct / partial / hallucinated).
- `report.md` — зведена таблиця і всі відповіді.

Фінальну оцінку ставимо самі: заповнюємо `verdict_manual` (correct / partial / hallucinated) і `invented_manual` (yes / no) у CSV, потім перераховуємо:

```bash
.venv/bin/python -m eval.run_eval --summarize eval/results/<дата>/results.csv
```

Кілька питань — пастки: у документації немає ендпоінтів для скасування refund (q05) чи повторного надсилання webhook (q10), а FAQ суперечить таблиці параметрів щодо довжини `statement_descriptor` (q02).
