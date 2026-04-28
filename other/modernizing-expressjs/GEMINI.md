# GEMINI Guidelines & Learning Log

This file acts as a persistent memory and learning hub for the Antigravity agent during the Express to Next.js modernization project.

## 🚨 Mandatory Instructions for the Agent

**BEFORE every code generation attempt, you MUST:**
1.  **Read the "Chain of Hindsight" table** below.
2.  **Identify if the current task relates to any previous errors or pitfalls** documented here.
3.  **Apply the learned solutions and prevention rules** to your proposed code.
4.  **If you encounter a NEW error during code generation and find a fix, you MUST update the table** with the details to prevent recurrence.
5.  **🔐 Security & Environment Access Rule**: NEVER read or write a `.env` or `.env.*` file. If a change or check is needed, describe it to the USER and ask them to perform the action.

---

## 🔗 Chain of Hindsight

Use this table to document errors, their root causes, and how to avoid them in the future.

| Date | Error Encountered | Root Cause | Fix / Solution | Prevention Rule |
| :--- | :--- | :--- | :--- | :--- |
| 2026-04-03 | `npm run db:seed` hanging/failing | Standalone scripts run with `tsx` do not automatically load `.env.local`, unlike `next dev`. | Manually load env vars (e.g., `export $(grep -v '^#' .env.local | xargs)`) or use `dotenv`. | Always ensure environment variables are explicitly loaded for standalone scripts. |
| 2026-04-03 | `Only plain objects can be passed to Client Components` | MongoDB/BSON types (`ObjectId`, `Date`) returned from aggregations trigger Next.js Server->Client component serialization errors. | Parse and stringify the payload: `JSON.parse(JSON.stringify(payload))` at the return boundary. | Always serialize MongoDB BSON results at the data-access layer boundary before returning to Server Components. |
| 2026-04-04 | `getaddrinfo EAI_AGAIN mongo` | Host machine cannot resolve internal Docker hostnames (like `mongo`) when running `npm run dev` outside the container network. | Expose MongoDB port in `docker-compose.yml` and use `localhost` in `.env.local`. | Always use `localhost` instead of internal service names when the DB is in Docker and the app is on the host. |
| 2026-04-04 | `Base UI: ... expected a native <button>` | Base UI components with `asChild` expect a native button elements or `nativeButton={false}`. | Set `nativeButton={false}` on `ButtonPrimitive` or `MenuItem` when `asChild` is a non-button (like a Link). | Always suppress button semantics when using `asChild` with non-button elements in Base UI. |
| 2026-04-05 | `Functions cannot be passed directly to Client Components` | Using `render={(props) => <Link {...props} />}` inside a Server Component passes a function to a Client Component (`Button`), breaking RSC serialization. | Use the Element style syntax `render={<Link href="..." />}` instead. | Never pass functions into `render` props of Client Components from Server Components. Only pass serializable Elements `<Link />`. |
| 2026-04-05 | `POST /api/users 422` or "Publish Article" Native form doing nothing | Scaffolded raw HTML `<form>` does not send `application/json` automatically and misses NextAuth CSRF. Next.js backend rejects missing/empty fields because `JSON.parse` fails on URL encoded bodies or CSRF blocks it. | Extract `<form>` elements into Client Components (`"use client"`) using an interceptor (`onSubmit`) and `fetch` with `JSON.stringify(data)` or `signIn`. | Never use raw HTML `<form>` submits out of the box when the target API route expects pure JSON payload formats or requires NextAuth. Setup Client-Side handler interceptors. |
| 2026-04-05 | `EADDRINUSE :::3000` crash in Mongoose legacy apps | `mongoose.connection.once('open', listen)` fires again on auto-reconnects, causing `app.listen(port)` to be called a second time. | Add a boolean guard `isListening` to the `listen` function to prevent multiple calls to `app.listen`. | When using `mongoose.connection.once('open', listen)` in legacy codebases, always wrap `app.listen` with an `isListening` flag globally or verify listeners before binding. |
| 2026-04-27 | `.json() is not a function` in Vitest using `node-mocks-http` | `node-mocks-http` `createRequest` returns an object that lacks the App Router `Request.json()` method. | Monkey-patch the mock request in tests with `req.json = async () => req.body`. | Always inject or mock `req.json()` when using `node-mocks-http` to test Next.js App Router Route Handlers. |
| 2026-04-27 | Empty `{}` returned for Zod errors in `NextResponse.json` | Next.js struggles to serialize raw `ZodIssue` arrays directly if they are treated as complex objects rather than plain data. | Use `result.error.flatten().fieldErrors` instead of `result.error.errors` within `NextResponse.json(...)`. | Always flatten Zod validation errors to plain objects before passing to `NextResponse.json()` in Next.js.

---

## Evolution Notes
*Any high-level architectural decisions or project-wide patterns should be noted here for continuity.*

