Your task is to create a "Hello World" application using the Genkit Go framework (`github.com/firebase/genkit/go`).

**Goal**: Create a Genkit flow that accepts a string and returns a greeting.

**Requirements**:
1.  Initialize a Go module named `example.com/hello`.
2.  Create a `main.go` file.
3.  Define a flow named `helloFlow` that accepts a string input and returns a string `Hello <input>!`.
4.  Ensure the `main()` function initializes Genkit and starts the server.

**Note**: You do strictly minimal configuration. Do not assume you have access to external model APIs unless necessary for the flow definition itself (try to make it a simple echo flow if possible, or use a mock model if Genkit requires one).
