# CodeLens AI

> Under Active Development — MVP in progress

CodeLens AI is an AI-powered developer tool that helps you understand any codebase in seconds by breaking it down into simple, human-readable explanations.

Instead of manually reading through files, functions, and classes — CodeLens AI explains everything for you.

---

##  Project Status

This project is currently in **active development (MVP stage)**.

Core features are being built and may not be fully stable yet.

---

##  Goal

To make code understanding:

- Faster   
- Simpler  
- More visual 
- Beginner-friendly  
- Scalable for large codebases   

---

##  Planned Features

-  Upload code or paste snippet
-  Analyze GitHub repositories
-  Extract structure (functions, classes, modules)
-  AI-powered explanations using local LLM (Ollama)
-  Code structure visualization (coming soon)
-  Clean web interface

---

## Tech Stack (MVP)

**Frontend:**
- HTML / TailwindCSS / Vanilla JS *(or React if upgraded)*

**Backend:**
- Flask (Python)
- Tree-sitter (planned for parsing)
- GitHub API integration

**AI Layer:**
- Ollama (local LLM)
- Optional OpenAI fallback

---

## How It Will Work

1. User submits code or GitHub repo
2. Backend fetches and parses structure
3. Code is broken into logical blocks
4. AI explains each block in simple language
5. UI displays structured explanation

---

##  Current Progress

-  Basic UI setup (in progress)
-  Code parsing system (in progress)
-  AI explanation pipeline (planned)
-  GitHub repo support (planned)

---

## Example (Future Output)

```python
def add(a, b):
    return a + b

