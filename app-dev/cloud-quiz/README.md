# Cloud Quiz

This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting started

1. Clone the repository
    ```bash
    git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
    ```
1. Navigate to the Cloud Quiz directory
    ```bash
    cd devrel-demos/app-dev/cloud-quiz/
    ```
1. Run the development server:
    ```bash
    npm run dev
    ```
1. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Make a change to the application

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

## Add a question

To add a question to the database, you will need to have access to the project. A project administrator will need to:

1. Visit https://console.firebase.google.com/project/cloud-quiz-next/settings/iam
1. Click `Add Member`
    * Role should be `Develop` -> `Admin`

## Run a live quiz

To run a live quiz, an admin or developer will need to add you as an `allowedGameLeader` in the database.

## Deploy on Cloud Run

```bash
gcloud run deploy cloud-quiz --source .
```
