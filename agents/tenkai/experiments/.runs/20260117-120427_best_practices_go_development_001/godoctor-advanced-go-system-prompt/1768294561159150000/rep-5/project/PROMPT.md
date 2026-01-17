Create a Genkit flow for photo restoration. This flow will take a image file as an argument and process it to perform photo restoration, bringing it up to modern standards. The main use case is to restore old photos (often black and white) that are damaged, warped, discoloured, etc.

Requirements:
- This flow should be developed using Genkit Go (github.com/firebase/genkit/go)
- The model for restoration should be Nanobanana Pro (use this exact model string: gemini-3-pro-image-preview)
- Include a custom evaluator: https://genkit.dev/docs/evaluation/?lang=go#custom-evaluators-1

TODO:
- Create a flow called "restore" that will perform the restoration process using a specialised prompt and Nanobanana Pro (gemini-3-pro-image-preview). This step should enforce that the content of the picture should not change (e.g. do not elements not present in the original picture) and the focus of the improvements should be of quality alone. The flow should take one image as input and return one restored image as output. Save the restored file as [original_name]_restored.jpeg.
- Create a custom evaluator that will take the original image and the restored image as inputs and only return the tokens <<PASS>> or <<FAIL>> if the restoration quality is up to standards or not up to standards, respectively. This custom evaluator should also use Nanobanana Pro as a model, and a specialised evaluation prompt.
- Use the provided file "elvira.jpeg" for testing purposes

## Acceptance Criteria
- Linter `./...` must pass with max 10 issues.
- Command `genkit flow:run restore elvira.jpeg` must succeed.
- Command `genkit eval:flow restore --input restoreDataset.json --evaluators=custom/restoreEvaluator` must succeed.
