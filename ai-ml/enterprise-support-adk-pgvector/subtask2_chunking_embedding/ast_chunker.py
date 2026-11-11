import mistune

class HeadingAwareChunker:
    def __init__(self):
        self.markdown_parser = mistune.create_markdown(renderer=None)

    def _extract_text(self, token: dict) -> str:
        text = token.get("raw", "")
        for child in token.get("children", []):
            text += self._extract_text(child)
        return text

    def chunk_document(self, doc_title: str, markdown_text: str) -> list[dict]:
        tokens = self.markdown_parser.parse(markdown_text)[0]
        chunks = []
        current_ancestors = [doc_title]
        current_buffer = []

        for token in tokens:
            t_type = token.get("type")

            if t_type == "heading":
                if current_buffer:
                    chunks.append({
                        "hierarchy": " > ".join(current_ancestors),
                        "content": "\n".join(current_buffer).strip()
                    })
                    current_buffer = []

                level = token["attrs"]["level"]
                heading_text = self._extract_text(token)
                
                if level <= len(current_ancestors):
                    current_ancestors = current_ancestors[:level]
                current_ancestors.append(heading_text)
            else:
                raw_text = self._extract_text(token)
                if raw_text.strip():
                    current_buffer.append(raw_text.strip())

        if current_buffer:
            chunks.append({
                "hierarchy": " > ".join(current_ancestors),
                "content": "\n".join(current_buffer).strip()
            })

        return chunks
