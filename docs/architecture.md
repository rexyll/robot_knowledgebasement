# Architecture

## Design principles

1. **Small core**: the base package uses only the Python standard library.
2. **Replaceable providers**: embedding, retrieval, and generation integrations are defined by interfaces, not hard-coded vendors.
3. **Provenance first**: document IDs, source paths, titles, and metadata travel with chunks.
4. **Incremental adoption**: ingest and inspect a Markdown file locally before adding external services.

## Initial data flow

```text
Markdown / text
      |
      v
  Markdown loader ------> KnowledgeDocument + metadata
      |
      v
  Text chunker ----------> DocumentChunk[]
      |
      +----> EmbeddingProvider (future adapter)
      |
      +----> Retriever (future vector / keyword / hybrid adapter)
                         |
                         v
                  SearchResult[]
                         |
                         v
                 LLM / RAG layer (future)
```

## Document identity and metadata

The initial loader computes a SHA-256 identifier from the source path and file contents. This is deterministic for an unchanged file at an unchanged path. Front matter supports common flat scalar values and inline lists. It is deliberately not a complete YAML parser; use a dedicated YAML dependency in an integration that needs nested YAML or advanced YAML syntax.

Recommended metadata fields:

- `title`: human-readable document title
- `category`: robots, sensors, actuators, navigation, manipulation, troubleshooting
- `robot`: robot/platform identifier
- `source`: upstream system, URL, or document identifier
- `version`: source document version
- `tags`: searchable domain terms
- `updated`: source update date

## Planned extension points

- Add PDF/HTML/ROS bag and log loaders under `ingest/`.
- Add embedding adapters under `embeddings/`.
- Add vector database and hybrid search adapters under `retrieval/`.
- Add answer synthesis, citations, and prompt policies under `llm/`.
- Keep secrets and raw customer/robot data outside Git.
