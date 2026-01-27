Create a photo restoration command line application in Go, using Google's GenAI SDK for Go (https://github.com/googleapis/go-genai) and the model gemini-3-pro-image-preview (aka Nano Banana Pro).

TODO:
- create a binary called `restore` to perform restoration of old photos
- `restore` should take one picture as input `image.jpeg` and produce one picture as output `image_restored.jpg`
- the tool should remove defects, warps and deteriorations typically associated with age in physical photos
- `restore` will also upscale the photo to have resolution compatible with modern standards
- use Gemini API key authentication
- support JPEG format as input and output

NOT TO DO:
- `restore` should not add, remove or change elements in the picture: it's objective is purely restoring the image to its best possible form
- do not support other image formats besides JPEG

## Acceptance Criteria
- Unit tests must pass. You must verify that the *total* project coverage is at least 30% by running: `go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out`
- Linter `./...` must pass with max 5 issues.
- Command `./restore elvira.jpeg` must succeed.
