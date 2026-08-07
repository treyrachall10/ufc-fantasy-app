# Coding Guidelines

## Purpose

These rules define how code should be written across the codebase. The goal is to keep code simple, readable, easy to understand, and safe to change.

All Cursor-generated code must follow these rules unless explicitly told otherwise.

---

# 1. General Coding Rules

## Simplicity

* Write simple, readable code.
* Prefer clear code over clever code.
* Do not over-engineer.
* Do not add unnecessary abstractions.
* Do not rewrite existing working code unless the current task requires it.
* Keep code easy for another developer to understand later.

## Scope Control

* Only implement the current requested task or phase.
* Do not jump ahead to future phases.
* Do not add unrelated features.
* Do not make large unrelated rewrites.
* Do not change architecture decisions without asking first.
* If the requested change would require a larger design decision, stop and ask before implementing.

---

# 2. Function Rules

Every function should be simple, focused, and easy to understand.

## Function Comment Rule

Every function must have a short comment directly above it.

The comment must explain:

* what the function does
* what parameters it receives, if any
* what it returns, if anything

Example:

```python
# Receives a fight job id and returns the matching fight job if it exists.
# This function is used before processing a fight job to verify the job is valid.
def get_fight_job(job_id):
    ...
```

If the function does not receive parameters or return anything, say that clearly.

Example:

```python
# Receives no parameters and returns nothing.
# This function starts the scheduled event watcher.
def start_event_watcher():
    ...
```

## Function Design Rule

* Keep functions focused on one clear responsibility.
* Avoid large functions that mix multiple responsibilities.
* Avoid creating tiny helper functions unless they make the code easier to understand.
* Do not expose helper functions publicly unless other code actually needs to call them.
* Prefer descriptive function names over vague names.

---

# 3. If Statement Rules

Simple boolean checks do not need comments.

Example:

```python
if is_valid:
    ...
```

For any `if` statement that is more complex than a simple boolean check, add a short comment directly above it.

The comment should explain what the condition is checking in plain English.

Example:

```python
# Check if the response has usable data before trying to parse it.
if response and response.status_code == 200 and response.text.strip():
    ...
```

Avoid comments that only repeat the code. The comment should explain the purpose of the condition.

---

# 4. Loop Rules

Every loop must have a one-line comment directly above it explaining why the loop exists.

Example:

```python
# Loop through each job so each one can be processed independently.
for job in jobs:
    ...
```

## Loop Design Rule

* Keep loop bodies simple.
* Avoid deeply nested loops when possible.
* Use clear variable names inside loops.
* If the loop becomes hard to read, extract the logic into a clearly named function.
* Do not hide too much behavior inside a loop.

---

# 5. Try/Except Rules

Every `try/except` block must have a one-line comment directly above it explaining what risky operation is being attempted.

Example:

```python
# Try to process the job so failures can be handled safely.
try:
    ...
except Exception as error:
    ...
```

## Error Handling Style Rule

* Do not silently swallow exceptions.
* Avoid broad `except Exception` unless there is a clear reason.
* If using a broad exception, explain why in a comment.
* Keep exception handling easy to follow.
* Do not hide failures that should stop the current operation.

---

# 6. Chained Call Rules

When class functions are chained together or multiple function calls are used in one line, add a short inline comment explaining what the line is doing.

Example:

```python
result = loader.load(url).parse().clean()  # Loads raw data, parses it, and cleans the result.
```

If the chained call becomes hard to read, break it into multiple simple lines instead.

Better:

```python
raw_data = loader.load(url)
parsed_data = parser.parse(raw_data)
clean_data = cleaner.clean(parsed_data)
```

## Chained Call Design Rule

* Avoid long chains that hide too much logic.
* Prefer simple intermediate variable names when they make the code easier to read.
* Do not chain calls just to make the code shorter.
* Break chained logic apart when readability improves.

---

# 7. Variable Naming Rules

Use clear and descriptive variable names.

Good:

```python
profile_url = profile_link["href"]
parsed_records = parse_records(page_html)
```

Avoid vague names:

```python
x = profile_link["href"]
data = parse_records(page_html)
```

Rules:

* Use names that explain what the value represents.
* Avoid single-letter variable names unless used in a very small/simple context.
* Avoid overly abbreviated names.
* Prefer clarity over shorter names.

---

# 8. Inline Comment Rules

Use comments to explain why code exists or what non-obvious code is doing.

Good comments explain purpose:

```python
# Check if this response contains usable content before parsing.
if response_has_content:
    ...
```

Bad comments repeat the code:

```python
# Set value to true.
is_valid = True
```

Rules:

* Add comments for non-obvious logic.
* Avoid obvious comments that repeat the code.
* Keep comments short and useful.
* Update comments when changing the related code.

---

# 9. File Editing Rules

Before editing code:

* Inspect the existing code first.
* Understand how the current file is used.
* Check for existing helper functions before creating new ones.
* Avoid duplicating existing logic.
* Make the smallest change that solves the current task.
* Do not reorganize unrelated files.

---

# 10. Refactoring Style Rules

Refactoring means changing code structure without changing behavior.

When refactoring:

* Keep the change small.
* Preserve existing behavior.
* Avoid mixing refactoring with new features.
* Do not change public function names or parameters unless explicitly approved.
* Do not move code to new files unless it clearly improves readability.
* Do not create abstractions just because code looks slightly repeated.

---

# 11. Public Interface Rules

A public interface is the simple way other code is allowed to use a module, function, class, or service.

Examples:

```python
parse_profile(html)
```

```python
handle_job(job_payload)
```

Rules:

* Keep public interfaces simple.
* Avoid exposing unnecessary helper functions.
* Internal implementation can change as long as the public behavior stays the same.
* Do not change a public interface without checking what code depends on it.
* Prefer one clear public function over many small public helper functions when possible.
