# Failed Tool Attempts: Scribble, Scalpel, and Endoscope/FetchWebpage

This report documents previous attempts to implement code editing and web crawling capabilities within the `godoctor` repository. These tools, while innovative, faced significant shortcomings that ultimately led to their deprecation.

---

## 1. Code Editing Tools: `scribble` (aka `write_code`) & `scalpel` (aka `edit_code`)

### Overview
The repository previously contained two tools dedicated to file manipulation: **`scribble`** (later renamed `write_code`) and **`scalpel`** (later renamed `edit_code`). Both were removed in commit `55d00ec` ("refactor: Remove unused tools and prompts") in favor of a cleaner slate, paving the way for the `proposal_smart_edit.md`.

### 1.1 `scribble` (aka `write_code`)

*   **Introduced in:** Commit `f8a8f03` ("feat: Add scribble tool and bump version")
*   **Refactored in:** Commit `dbdd642` ("refactor(scribble): Improve error handling for invalid Go code")
*   **Purpose:** To create new files or completely overwrite existing ones. The tool's description stated: "Creates or replaces an entire Go source file with the provided content. Use this tool when the extent of edits to a file is substantial, affecting more than 25% of the file's content. It automatically formats the code and manages imports."
*   **Mechanism:** Accepted `file_path` and `content`. It first wrote the file to disk, then ran `gopls check` for syntax validation, followed by `goimports` and `gofmt` for standardization.
*   **Strengths:**
    *   **Automated Go Formatting:** Automatically handled `goimports` and `gofmt` after writing, reducing the burden on the LLM to produce perfectly formatted Go code. This was a valuable feature for maintaining code consistency.
*   **Critical Weaknesses:**
    *   **Catastrophic Data Loss Bug:** The tool utilized a "write-then-validate" approach. It would overwrite the target file *immediately* with the new content. If the subsequent `gopls check` failed due to invalid Go code (e.g., a syntax error introduced by the LLM), the tool's error handling would `os.Remove` the file to "cleanup" the invalid state.
        *   *Scenario:* If an LLM attempted to edit an existing, critical 1000-line file but inadvertently introduced a syntax error, the tool would first overwrite the file, detect the error during validation, and then tragically delete the original source code. This made it extremely dangerous for real-world use.
    *   **Runtime Dependency:** Had a hard dependency on the `gopls` binary being installed and available in the system's `$PATH`, which could lead to environment-specific failures.

### 1.2 `scalpel` (aka `edit_code`)

*   **Introduced/Improved in:** Commit `26229ce` ("feat(tools): Add endoscope tool and improve scalpel error handling") - Note: `scalpel` existed prior but this commit significantly improved its error handling logic.
*   **Purpose:** To perform surgical, text-based replacements within a file. Its description highlighted: "Edits a Go source file by applying a series of replacements. Each replacement consists of an 'old_string' and a 'new_string'. This tool is ideal for surgical edits like adding, deleting, or renaming code, especially when multiple changes are required. To ensure precision, each 'old_string' must be a unique anchor string that includes enough context to target only the desired location."
*   **Mechanism:** Accepted a `file_path` and a slice of `Edits` (each an `OldString` -> `NewString` pair). It read the file's content, then iterated through the `Edits` applying `strings.Replace(content, edit.OldString, edit.NewString, 1)` for each. It also included `gopls check`, `goimports`, and `gofmt` steps.
*   **Strengths:**
    *   **Safe Revert Mechanism:** Critically, `scalpel` read the `originalContent` into memory *before* making any changes. If the resulting modified code failed `gopls check`, it would physically revert the file on disk to its original content, preventing data corruption or introduction of invalid code.
    *   **Fuzzy Suggestions:** If an `old_string` was not found during the exact match, the tool used the `github.com/sahilm/fuzzy` library to suggest similar lines from the file (up to 3 suggestions). This was a strong feature for helping LLMs correct "hallucinated context" where they might misremember exact string literals.
*   **Weaknesses:**
    *   **Silent Partial Failure:** The tool looped through all `edits`. If only a subset of the `OldString` values matched and were replaced, the operation was still reported as a success. This meant if an LLM intended to perform 3 distinct edits but only the first one matched, the other 2 were silently ignored, leading to incomplete and potentially confusing refactors.
    *   **Brittle Exact Matching:** Despite the fuzzy suggestion fallback, the primary replacement mechanism relied on exact string matching. Any minor difference (e.g., whitespace, indentation, comments) between the LLM's `old_string` and the actual content on disk would cause a failure to match.
    *   **Runtime Dependency:** Like `scribble`, it had a hard dependency on the `gopls` binary for Go code validation.

### **Summary of Lessons Learned from Code Editing Tools:**
1.  **Validation Safety is Paramount:** Never risk data loss. A "read, modify in memory, validate, then write or revert" strategy is essential. `scalpel`'s revert logic was a critical improvement over `scribble`'s delete logic.
2.  **All-or-Nothing Atomic Edits:** For complex refactoring, an `edit_code` tool must ensure that *all* intended changes are applied successfully, or the entire operation is rolled back. Partial application creates ambiguity and silent failures.
3.  **Resilient Matching:** Exact string matching is too brittle for LLM-driven code editing. The fuzzy matching in `scalpel` was a good start, and future tools should explore more sophisticated AST-based or semantic matching.

---

## 2. Web Crawling Tool: `endoscope` (aka `fetch_webpage`)

### Overview
The `endoscope` tool (later renamed `fetch_webpage`) was designed to crawl websites. It was removed in commit `902e2ed` ("refactor: remove namespace from tools").

### 2.1 `endoscope` (aka `fetch_webpage`)

*   **Introduced in:** Commit `26229ce` ("feat(tools): Add endoscope tool and improve scalpel error handling")
*   **Renamed in:** Commit `97b6ae3` ("refactor(tools): rename tools to be more LLM-friendly")
*   **Purpose:** To recursively crawl a website to a specified depth, extracting and returning the text-only content of each page. The tool's description stated: "Crawls a website to a specified depth, returning the text-only content of each page. This tool is useful for summarizing web pages, analyzing content, or answering questions about a website's content."
*   **Inputs:**
    *   `URL`: The starting URL for the crawl.
    *   `Level`: The maximum depth of the crawl (e.g., `0` for only the initial page, `1` for the initial page and all pages directly linked from it).
    *   `External`: A boolean flag to control whether links to external domains should be followed (`true`) or restricted to the base domain (`false`).
*   **Implementation:**
    *   Utilized a standard Breadth-First Search (BFS) queue to manage the URLs to visit.
    *   Parsed HTML documents using the `golang.org/x/net/html` package.
    *   Extracted text content from a predefined set of semantic HTML tags (e.g., `p`, `h1-h6`, `li`, `td`, `th`, `a`, `blockquote`, `span`, `strong`, `em`, `b`, `i`, `code`, `pre`), filtering out most structural and scripting elements.
    *   Returned a JSON object containing a `CrawlResult` struct, which included a slice of `Result` objects (each with `URL`, `Title`, and extracted `Content`) and a slice of `CrawlError` objects for any pages that failed to process.
*   **Strengths:**
    *   **Recursive Crawling for Context:** Unlike simple "fetch URL" tools, `fetch_webpage` could recursively traverse a documentation or knowledge base site. This capability is highly valuable for an LLM needing to gather broad, interconnected context from external sources.
    *   **Content Filtering/Noise Reduction:** By selectively extracting text from content-bearing HTML tags, it effectively filtered out much of the irrelevant HTML boilerplate (e.g., `<script>`, `<style>`, navigation elements not containing primary text), saving precious token usage compared to fetching and processing raw HTML.
    *   **Robustness in Failure:** The crawler was designed to continue processing even if individual pages failed to fetch or parse. Errors were collected and returned in a dedicated `Errors` field within the `CrawlResult`, allowing the LLM to understand which parts of the crawl succeeded and which failed.
*   **Weaknesses:**
    *   **Context Window Token Explosion:** The most significant weakness was its output strategy. It returned the **full, aggregated text content** of every crawled page in a single, potentially massive JSON response. A depth-2 crawl of even a moderately sized documentation site could easily generate hundreds of thousands of tokens, instantly overflowing the context window of most LLMs and making the tool impractical for anything beyond very shallow crawls.
    *   **Naive Text Formatting:** While it extracted text, the method of concatenating strings with simple spaces often destroyed the semantic structure inherent in HTML (e.g., tables, nested lists, code blocks). This resulted in a flat, difficult-to-parse blob of text, losing valuable information that could have aided an LLM's understanding.
    *   **Sequential Processing:** The crawling mechanism was single-threaded. For larger `Level` values or sites with many links, the crawl could be very slow, leading to long response times.
    *   **Missing Web Standards:** The implementation lacked adherence to common web crawling best practices, such as respecting `robots.txt` directives or setting a custom `User-Agent` header, which could lead to sites blocking the crawler or legal/ethical issues.

### **Recommendation for Resurrection:**
If the `fetch_webpage` tool were to be resurrected, significant architectural changes would be required to address its fundamental limitations, particularly the token explosion issue:
1.  **Iterative/Paged Results:** Instead of a single massive response, the tool should return results iteratively or in a paginated fashion. For example, it could return a list of discovered URLs and their titles, allowing the LLM to explicitly request the content of specific pages as needed.
2.  **Markdown Conversion for Structure:** Implement a robust HTML-to-Markdown conversion (e.g., using a library like `github.com/JohannesKaufmann/html-to-markdown`). This would preserve the semantic structure of the content (headers, lists, tables, code blocks) in a token-efficient and LLM-friendly format.
3.  **Asynchronous/Concurrent Fetching:** Introduce concurrency to speed up crawling.
4.  **Respect `robots.txt`:** Implement logic to parse and respect `robots.txt` rules.
5.  **Configurable User-Agent:** Allow setting a custom `User-Agent` string.
6.  **Optional Headless Browser Integration:** For advanced scenarios involving JavaScript-rendered Single Page Applications (SPAs), consider optional integration with a headless browser (e.g., via `chromedp`), though this would add significant complexity and runtime dependencies. This might be overkill for a CLI tool, but worth noting the limitation.

---

**End of Report.**
