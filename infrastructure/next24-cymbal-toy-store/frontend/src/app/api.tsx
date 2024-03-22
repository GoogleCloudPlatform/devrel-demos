type History = Array<{
  text: string;
  role: string;
}>

export function api(history: History) {
  const prefix = process.env.NODE_ENV === "development" ? "http://localhost:5002" : ""

  return fetch(`${prefix}/api/chat`, {
    method: "POST",
    body: JSON.stringify(history)
  })
}
