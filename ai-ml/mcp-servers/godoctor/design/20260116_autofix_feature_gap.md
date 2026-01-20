# Feature Gap: Autofix (Edit Distance Typo Correction)

## Problem Statement
The original `smart_edit` tool had an intelligent typo correction feature called **Autofix**. This feature is currently **missing** from the godoctor `file.edit` implementation.

## Missing Capability

### Original Autofix Behavior
When the agent made a typo in code (e.g., `ftm.Println` instead of `fmt.Println`), the original tool would:

1. **Detect the error** during syntax/type checking
2. **Use edit distance** (Levenshtein) to find similar valid identifiers
3. **Suggest the correction** with confidence score (e.g., "ftm.Println not found, did you mean fmt.Println?")
4. **Auto-apply the fix** if confidence was high enough (e.g., distance ≤ 2)

### Current Behavior
The current `file.edit`:
- Uses `goimports` for formatting and import organization
- Rejects invalid code with an error message
- Does NOT attempt to correct typos

## Proposed Implementation

### Parameters
```go
type Params struct {
    Filename        string  `json:"filename"`
    SearchContext   string  `json:"search_context"`
    Replacement     string  `json:"replacement"`
    Threshold       float64 `json:"threshold,omitempty"`
    Autofix         bool    `json:"autofix,omitempty"`      // NEW: Enable typo correction
    AutofixMaxDist  int     `json:"autofix_max_dist,omitempty"` // NEW: Max edit distance (default: 2)
}
```

### Logic Flow
1. Parse the edited Go file
2. Run type checker to find undefined identifiers
3. For each undefined identifier:
   - Search for similar symbols in scope (using Levenshtein distance)
   - If `distance <= AutofixMaxDist` and single best match exists:
     - Apply the fix automatically
   - Else:
     - Return hint: "Did you mean X?"
4. Re-run `goimports` on corrected code

### Example
**Agent submits:**
```go
ftm.Println("Hello")
```

**Autofix detects:**
- `ftm` is undefined
- `fmt` is a known package with distance 1
- Confidence: HIGH

**Result:** Automatically corrects to `fmt.Println("Hello")` and returns success with note:
> "Autofixed: ftm → fmt (edit distance: 1)"

## Priority
**Medium** - This reduces friction for agents making minor typos, but the current hint system already provides guidance for manual correction.

## Dependencies
- `go/types` for type checking
- Levenshtein implementation (already exists in `edit.go`)
- Symbol scope resolution
