# 4. AI & RAG Architecture

## 4.1 AI Provider Abstraction (Strategy Pattern)

```python
# ai/providers/base.py

from abc import ABC, abstractmethod
from typing import Iterator

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Generate a complete response."""
        pass
    
    @abstractmethod
    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        """Stream response tokens."""
        pass
    
    @abstractmethod
    def structured_output(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        """Generate structured JSON response."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        """Return model name, provider, and capabilities."""
        pass
```

```python
# ai/providers/groq_provider.py

from groq import Groq

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = 'llama-3.3-70b-versatile'):
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def complete(self, messages, **kwargs):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024),
        )
        return response.choices[0].message.content
    
    def stream(self, messages, **kwargs):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024),
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def structured_output(self, messages, schema, **kwargs):
        # Use JSON mode with schema instruction in system prompt
        system_msg = f"Respond ONLY with valid JSON matching this schema: {json.dumps(schema)}"
        messages = [{"role": "system", "content": system_msg}] + messages
        response = self.complete(messages, **kwargs)
        return json.loads(response)
```

```python
# ai/providers/factory.py

class LLMProviderFactory:
    _providers = {
        'groq': GroqProvider,
        # Future: 'ollama': OllamaProvider, 'huggingface': HuggingFaceProvider
    }
    
    @staticmethod
    def create(provider_name: str = None) -> LLMProvider:
        provider_name = provider_name or os.environ.get('LLM_PROVIDER', 'groq')
        provider_class = LLMProviderFactory._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        return provider_class(
            api_key=os.environ.get(f'{provider_name.upper()}_API_KEY'),
            model=os.environ.get(f'{provider_name.upper()}_MODEL')
        )
```

## 4.2 AI Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AI SERVICE LAYER                     │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  TicketAIService │  │  ChatAIService               │  │
│  │                  │  │                               │  │
│  │ classify()       │  │ chat(query, history)          │  │
│  │ predict_priority │  │ stream_chat(query, history)   │  │
│  │ route_department │  │ summarize(text)               │  │
│  │ suggest_replies  │  │ extract_actions(text)         │  │
│  │ summarize_ticket │  │ generate_email(context)       │  │
│  │ find_similar()   │  │ generate_report(data)         │  │
│  └────────┬─────────┘  └──────────────┬───────────────┘  │
│           │                           │                   │
│           └─────────┬─────────────────┘                   │
│                     ▼                                     │
│  ┌──────────────────────────────────────────────────────┐│
│  │              PromptManager                           ││
│  │  load_template(name) → interpolate(variables)       ││
│  │  Templates stored in DB (admin-configurable)        ││
│  └──────────────────────┬───────────────────────────────┘│
│                         ▼                                 │
│  ┌──────────────────────────────────────────────────────┐│
│  │          LLMProvider (via Factory)                   ││
│  │          complete() | stream() | structured()       ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### AI Feature Implementations

| Feature | Input | Prompt Strategy | Output Schema |
|---------|-------|----------------|---------------|
| Ticket Classification | title + description | System: "Classify into categories..." + Few-shot examples | `{category, confidence}` |
| Priority Prediction | title + description + category | System: "Predict priority level..." + Criteria definitions | `{priority, confidence, reasoning}` |
| Department Routing | title + description + departments list | System: "Route to department..." + Department descriptions | `{department_id, confidence}` |
| Suggested Replies | ticket context + KB results | System: "Generate professional replies..." | `{replies: [{text, tone}]}` |
| Ticket Summary | ticket + all comments | System: "Summarize this ticket..." | `{summary, key_issues, action_items, sentiment}` |
| Root Cause Analysis | incident + linked tickets | System: "Analyze root cause..." + RAG context | `{root_cause, evidence, remediation}` |
| Email Generation | ticket context + email type | System: "Generate professional email..." | `{subject, body}` |
| Action Extraction | conversation text | System: "Extract action items..." | `{actions: [{action, assignee, deadline}]}` |

## 4.3 RAG Pipeline Architecture

### Document Ingestion Pipeline

```
                    ┌─────────────┐
                    │   Upload    │
                    │  (API/UI)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Validate  │  File type, size, virus scan
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Store     │  Cloudinary (prod) / Local (dev)
                    │   Raw File  │  Save metadata to PostgreSQL
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │   Celery Background     │
              │   Task: process_doc     │
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │   Extract   │  PDF → PyPDF2/pdfplumber
                    │   Text      │  DOCX → python-docx
                    └──────┬──────┘  TXT/MD → direct read
                           │
                    ┌──────▼──────┐
                    │   Clean     │  Remove headers/footers
                    │   Text      │  Normalize whitespace
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Chunk     │  512 tokens per chunk
                    │   Text      │  50 token overlap
                    └──────┬──────┘  RecursiveCharacterTextSplitter
                           │
                    ┌──────▼──────┐
                    │   Embed     │  sentence-transformers
                    │   Chunks    │  all-MiniLM-L6-v2 (384d)
                    └──────┬──────┘  Batch processing
                           │
                    ┌──────▼──────┐
                    │   Store     │  ChromaDB collection
                    │   Vectors   │  Metadata: doc_id, chunk_idx,
                    └──────┬──────┘  page_num, source
                           │
                    ┌──────▼──────┐
                    │   Update    │  PostgreSQL: document status
                    │   Status    │  → "processed"
                    └─────────────┘
```

### RAG Query Pipeline

```
User Query
    │
    ▼
┌──────────────────┐
│ 1. Embed Query   │  MiniLM-L6-v2 → 384d vector
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Vector Search │  ChromaDB.query(embedding, n_results=5)
│    + Metadata    │  Filter by: collection, doc_type, department
│    Filtering     │  Returns: chunks + similarity scores
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Score Filter  │  Discard chunks with similarity < 0.5
│    + Re-rank     │  Sort by relevance
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Build Context │  Combine top chunks into context block
│    Window        │  Include source metadata for citations
└────────┬─────────┘  Stay within model context window (8192 tokens)
         │
         ▼
┌──────────────────┐
│ 5. Construct     │  System: "Answer using ONLY the provided context..."
│    Prompt        │  Context: [retrieved chunks with sources]
└────────┬─────────┘  User: [original query]
         │
         ▼
┌──────────────────┐
│ 6. LLM Generate  │  Groq API (streaming)
│    (Stream)      │  Temperature: 0.3 (factual)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. Format        │  Attach citations: [Source: doc, Section: X]
│    Response      │  Calculate confidence from avg similarity
└──────────────────┘  Return with metadata
```

### ChromaDB Collection Design

| Collection | Content | Metadata |
|-----------|---------|----------|
| `documents` | Uploaded PDF/DOCX/TXT chunks | doc_id, chunk_index, page_num, doc_type, department_id |
| `knowledge_articles` | Knowledge base article chunks | article_id, chunk_index, category, tags |
| `tickets` | Ticket title + description embeddings | ticket_id, status, category, department_id |

## 4.4 Prompt Template System

```python
# Example prompt template (stored in PostgreSQL, editable via Admin UI)

{
    "name": "ticket_classification",
    "version": 2,
    "system_prompt": """You are an IT service desk AI assistant. 
Classify the following support ticket into exactly ONE category.

Available categories: {categories}

Respond with JSON: {{"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}}""",

    "user_prompt": """Ticket Title: {title}
Ticket Description: {description}""",

    "variables": ["categories", "title", "description"],
    "model_params": {
        "temperature": 0.2,
        "max_tokens": 200
    }
}
```

## 4.5 AI Graceful Degradation

| Failure Scenario | Behavior |
|-----------------|----------|
| Groq API timeout (>30s) | Return error with retry suggestion; ticket created without AI metadata |
| Groq API rate limit (429) | Queue request for retry via Celery; return partial result |
| Groq API down (5xx) | Log error; all AI features show "AI temporarily unavailable" badge |
| ChromaDB unavailable | Fall back to PostgreSQL full-text search for knowledge queries |
| Embedding model load failure | Skip embedding; mark document as "pending_processing" |
| Invalid LLM response (malformed JSON) | Retry once with stricter prompt; fall back to default values |

All core ticket/incident operations continue normally even when AI is unavailable.
