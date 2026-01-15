Create a command line application called "restore". This application will take a image file, like image.jpeg, as an argument and process it to perform photo restoration, bringing it up to modern standards. The main use case is to restore old photos (often black and white) that are damaged, warped, discoloured, etc. It can also be used to take a low resolution file and upscale it.

Requirements:
- The CLI should be developed in Go
- The core of the CLI will be the nano banana pro model (gemini-3-pro-image-preview)
- The SDK used should be Genkit Go (github.com/firebase/genkit/go)

TODO:
- Create a flow called "analyse" that will assess the picture for the improvements that should be made. This flow should produce a list of recommendations to be applied to the picture to bring it up to modern standards
- Create a flow called "repair" that will take a set of repair instructions and use the model (nano banana pro) to perform those edits. This step should enforce that the content of the picture should not change (e.g. do not elements not present in the original picture) and the focus of the improvements should be of quality alone
- Create a flow called "validate" that will assess the quality of the repair comparing the original picture with the restored one. This flow should also use nano banana pro.
- If the validate flow finds major defects in the picture, the application should try the repair again, up to 3 times, for when the application will either succeed (exit status 0) or return an error (exit status 1)
- Store prompts for reusability using dotprompt (suported by Genkit)
- The restored file is saved as <original_name>_restored.<original_extension>
- If multiple restored files are present, add a sequence number after _restored e.g. _restored_1 - do not overwrite files
- Include flags to display help and perform intermediate steps only e.g. --validate --analyse and --restore-only - this will be helpful for debugging purposes

Acceptance Criteria
- `go build . -o restore` compiles without errors
- Test coverage > 50%
- Lint issues <= 5 (using `golangci-lint run`)
- Running "restore" with no arguments displays a help message
- Running "restore" with an image as argument performs the restoration
- A picture called "elvira.jpeg" is provided for tests. A successful restoration of this picture is required. (An LLM will be the judge)