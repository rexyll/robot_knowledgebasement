# Ingestion quick guide

The first release supports local Markdown files and standard-library text handling.

## Inspect a document

```bash
robot-kb inspect knowledge/navigation/differential-drive-odometry.md
```

## Preview chunks

```bash
robot-kb chunk knowledge/navigation/differential-drive-odometry.md \
  --chunk-size 1000 --overlap 150
```

Both commands print JSON to stdout and do not modify source files or write to the data directories.

## Python API

```python
from robot_knowledgebase.ingest import chunk_document, load_markdown

document = load_markdown("knowledge/navigation/differential-drive-odometry.md")
chunks = chunk_document(document, chunk_size=1000, overlap=150)
```
