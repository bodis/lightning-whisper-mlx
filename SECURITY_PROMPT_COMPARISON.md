# Security Prompt Comparison: Before vs After

**Test Case**: Path traversal vulnerability in `save_processed_audio()` (lightning_whisper_mlx/audio.py)

---

## 🔴 **Original Prompt - Why It Failed**

### What Was Missing:

Your original prompt mentioned "Input Validation" but **never explicitly covered**:
- ❌ Path traversal attacks
- ❌ Directory traversal
- ❌ File path validation patterns
- ❌ `os.path.join()` with user input
- ❌ Missing `os.path.basename()` sanitization
- ❌ Arbitrary file read/write vulnerabilities

### Closest Section:

```markdown
### 12. Input Validation
- Is all user input validated?
- Whitelist vs blacklist approach?
- File upload validation?
```

**Problem**: Too generic! Doesn't mention:
- File **paths** as user input
- Path traversal **patterns** (`../`)
- Specific **functions** to check (`os.path.join`, `os.makedirs`)
- How to **validate** file paths properly

### What It Caught:

✅ **MD5 Usage** (line 77, 110):
```markdown
### 11. Cryptography
- Weak algorithms (MD5, SHA1, DES)?
```

**Result**: Found MD5, but marked as HIGH severity when it's only MEDIUM for cache keys.

### What It Missed:

❌ **Path Traversal** (line 46):
```python
def save_processed_audio(audio_data, cache_dir, filename):
    cache_path = os.path.join(cache_dir, filename)  # ← No validation!
    np.save(cache_path, data)  # ← Arbitrary file write!
```

**Why**: Prompt doesn't mention path traversal or file path validation patterns.

---

## ✅ **Improved Prompt - What Changed**

### New Section Added:

```markdown
### 2. Path Traversal & File Operations (CWE-22)

- **Path Traversal Attacks:**
  - Check for `../` or `..\` sequences in file paths from user input
  - Look for user-controlled paths in file operations
  - Verify paths stay within intended boundaries

- **Dangerous File Operations:**
  - `os.path.join()` with unsanitized user input
  - `open()`, `read()`, `write()` with user-controlled paths
  - `os.makedirs()` with user input (arbitrary directory creation)
  - `np.save()`, `np.load()`, `pickle.load()` with user paths

- **Missing Path Validation:**
  - Is `os.path.basename()` used to strip directory components?
  - Is `os.path.realpath()` or `os.path.abspath()` used to resolve symlinks?
  - Are resolved paths checked against allowed base directories?

- **Vulnerable Patterns to Flag:**
  ```python
  # CRITICAL - Arbitrary file write
  def save_cache(cache_dir, filename, data):
      path = os.path.join(cache_dir, filename)  # filename can be "../../../etc/passwd"
      with open(path, 'w') as f:
          f.write(data)
  ```
```

### Enhanced Critical Patterns List:

```markdown
## Critical Patterns to Always Flag

**Immediate Red Flags (CRITICAL severity):**
4. File operations with unsanitized user paths  ← NEW!

**High Priority Flags:**
1. os.path.join() without os.path.basename() on user input  ← NEW!
```

### Improved Severity Guidelines:

```markdown
**Special Cases:**
- **MD5 for cache keys:** Severity = medium (suggest usedforsecurity=False)
- **MD5 for passwords:** Severity = critical
- **Path traversal + write:** Severity = critical (RCE)  ← NEW!
- **Path traversal + read:** Severity = high  ← NEW!
```

---

## 📊 **Expected Results Comparison**

### With Original Prompt:

```json
{
  "findings": [
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 77,
      "severity": "high",
      "category": "security",
      "message": "Use of weak MD5 hash for security.",
      "suggestion": "Consider usedforsecurity=False"
    }
  ]
}
```

**Issues Found**: 1 (MD5)
**Critical Issues**: 0
**Path Traversal**: ❌ MISSED

---

### With Improved Prompt:

```json
{
  "findings": [
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 46,
      "severity": "critical",
      "category": "security",
      "message": "Path traversal vulnerability: User-controlled 'filename' parameter is passed to os.path.join() without sanitization. The save_processed_audio() function allows arbitrary file write via '../' sequences in the filename.",
      "suggestion": "Sanitize filename with os.path.basename() to strip directory components: 'filename = os.path.basename(filename)'. Then validate the final path stays within cache_dir: 'if not os.path.abspath(cache_path).startswith(os.path.abspath(cache_dir)): raise ValueError(\"Path traversal detected\")'"
    },
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 79,
      "severity": "high",
      "category": "security",
      "message": "Path traversal vulnerability: User-controlled 'cache_dir' parameter in load_audio() allows reading files from arbitrary locations. Combined with np.load() on line 83, this enables arbitrary file read.",
      "suggestion": "Validate cache_dir is within allowed boundaries: 'cache_dir = os.path.abspath(cache_dir); if not cache_dir.startswith(ALLOWED_CACHE_ROOT): raise ValueError(\"Invalid cache directory\")'"
    },
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 43,
      "severity": "high",
      "category": "security",
      "message": "Arbitrary directory creation: os.makedirs() with user-controlled cache_dir parameter allows creating directories anywhere the process has permissions.",
      "suggestion": "Validate cache_dir before creating: 'cache_dir = os.path.abspath(cache_dir); if not cache_dir.startswith(ALLOWED_BASE): raise ValueError(\"Invalid directory\")'"
    },
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 77,
      "severity": "medium",
      "category": "security",
      "message": "Weak hash function: MD5 is used for cache key generation. While acceptable for non-security purposes, add usedforsecurity=False to clarify intent and suppress warnings.",
      "suggestion": "hashlib.md5(file.encode(), usedforsecurity=False).hexdigest()"
    },
    {
      "file_path": "lightning_whisper_mlx/audio.py",
      "line_number": 110,
      "severity": "medium",
      "category": "security",
      "message": "Weak hash function: MD5 is used for cache key generation. While acceptable for non-security purposes, add usedforsecurity=False to clarify intent and suppress warnings.",
      "suggestion": "hashlib.md5(file.encode(), usedforsecurity=False).hexdigest()"
    }
  ]
}
```

**Issues Found**: 5 (3 path traversal + 2 MD5)
**Critical Issues**: 1 ✅
**Path Traversal**: ✅ DETECTED

**PR Status**: ❌ **BLOCKED** (1 critical, 0 allowed per config)

---

## 🎯 **Impact Analysis**

### Original Prompt Results:
- ✅ Found: MD5 usage (low-priority issue)
- ❌ Missed: Path traversal (CRITICAL security flaw)
- ❌ PR would have been: **MERGED** (no critical issues)
- 🚨 **Result**: Critical vulnerability in production!

### Improved Prompt Results:
- ✅ Found: Path traversal (CRITICAL)
- ✅ Found: Arbitrary file write (CRITICAL)
- ✅ Found: Arbitrary file read (HIGH)
- ✅ Found: MD5 usage (MEDIUM, correct severity)
- ✅ PR would be: **BLOCKED** (critical issues found)
- ✅ **Result**: Vulnerability caught before merge!

---

## 📋 **Specific Code Patterns Now Detected**

### Pattern 1: Unsanitized os.path.join()

```python
# VULNERABLE (line 46)
cache_path = os.path.join(cache_dir, filename)  # ← AI will flag this!
np.save(cache_path, data)

# Exploit: filename = "../../../etc/cron.d/backdoor"
```

**Detection**: AI sees `os.path.join()` with parameter `filename` that comes from function argument (untrusted). No `os.path.basename()` sanitization before join.

### Pattern 2: Arbitrary File Write

```python
# VULNERABLE (line 49)
np.save(cache_path, np.array(audio_data))  # ← AI flags this too!

# Where cache_path = os.path.join(cache_dir, filename) with unsanitized inputs
```

**Detection**: AI traces data flow from unsanitized `filename` → `cache_path` → `np.save()`.

### Pattern 3: Arbitrary Directory Creation

```python
# VULNERABLE (line 43)
os.makedirs(cache_dir, exist_ok=True)  # ← AI flags user-controlled path!
```

**Detection**: AI sees `cache_dir` comes from function parameter (untrusted), used directly in `os.makedirs()`.

### Pattern 4: Arbitrary File Read

```python
# VULNERABLE (line 79-84)
if cache_dir:
    cache_path = os.path.join(cache_dir, cache_filename)
    if os.path.exists(cache_path):
        cached_audio = np.load(cache_path)  # ← AI flags this!
```

**Detection**: AI sees user-controlled `cache_dir` enables reading from arbitrary locations.

---

## 🔧 **How AI Uses the Improved Prompt**

### Step 1: Identify User Input
AI traces which variables come from function parameters:
- ✅ `filename` in `save_processed_audio(audio_data, cache_dir, filename)`
- ✅ `cache_dir` in both functions

### Step 2: Check Dangerous Functions
AI scans for file operations with those variables:
- ✅ `os.path.join(cache_dir, filename)` ← User input!
- ✅ `os.makedirs(cache_dir)` ← User input!
- ✅ `np.save(cache_path, ...)` ← Derived from user input!
- ✅ `np.load(cache_path)` ← Derived from user input!

### Step 3: Check for Sanitization
AI looks for protective patterns:
- ❌ No `os.path.basename(filename)` before join
- ❌ No `os.path.abspath()` boundary check
- ❌ No validation against allowed directories
- ❌ No whitelist of allowed paths

### Step 4: Flag as Critical
AI sees:
- User input → file operation
- No sanitization
- Write access (arbitrary file write = RCE potential)
- **Verdict**: CRITICAL severity

---

## ✅ **Implementation Checklist**

To update your security prompt:

1. **Add new section** "Path Traversal & File Operations" after Injection
2. **Update numbering** for subsequent sections (Auth becomes #3, etc.)
3. **Add to Critical Patterns** list:
   - File operations with unsanitized user paths (CRITICAL)
   - os.path.join() without os.path.basename() (HIGH)
4. **Add to Severity Guidelines**:
   - Path traversal + write = CRITICAL
   - Path traversal + read = HIGH
   - MD5 for cache keys = MEDIUM
5. **Test with this PR** to verify it catches the vulnerability

---

## 📈 **Success Metrics**

After updating the prompt, test with this PR. You should see:

**Static Analysis** (unchanged):
- ✅ Bandit: 2 HIGH (MD5 usage)
- ✅ Ruff: 4 issues (MD5 usage, subprocess, assert)

**AI Security Review** (NEW):
- ✅ 1 CRITICAL: Path traversal with arbitrary file write
- ✅ 2 HIGH: Path traversal read, arbitrary directory creation
- ✅ 2 MEDIUM: MD5 for cache keys

**PR Status**:
- ❌ **BLOCKED**: Critical issues: 1 found, 0 allowed
- 💬 **Comments**: Specific line-by-line feedback on vulnerable code

**Validation**: ✅ **Critical vulnerability detected and blocked!**

---

## 🎓 **Key Lesson**

**Security prompts must be explicit**. Generic phrases like "validate input" aren't enough. You need:

1. **Specific attack patterns** (`../` in paths)
2. **Specific functions to check** (`os.path.join`, `np.save`)
3. **Specific validation patterns** (`os.path.basename()`, boundary checks)
4. **Example vulnerable code** (so AI recognizes the pattern)
5. **Example secure code** (so AI knows how to fix it)

Your original prompt was good for common vulnerabilities (SQL injection, XSS), but path traversal required explicit instruction.

---

**Bottom Line**: Update your security prompt with the "Path Traversal & File Operations" section from `IMPROVED_SECURITY_PROMPT.md`, and your AI review will catch these critical vulnerabilities! 🎯
