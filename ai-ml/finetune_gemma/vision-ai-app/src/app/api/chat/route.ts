import { NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export async function POST(req: Request) {
  try {
    const { url, messages, model } = await req.json();

    if (!url) {
      return NextResponse.json({ error: "No target URL provided" }, { status: 400 });
    }

    const auth = new GoogleAuth();
    const client = await auth.getIdTokenClient(url);
    
    // vLLM / OpenAI compatible endpoint
    const endpoint = `${url.replace(/\/$/, "")}/v1/chat/completions`;
    
    const response = await client.request({
      url: endpoint,
      method: "POST",
      data: {
        model: model || "google/gemma-3-27b-it",
        messages,
        max_tokens: 1024,
        stream: true,
      },
      responseType: "stream",
    });

    const stream = new ReadableStream({
      async start(controller) {
        const reader = (response.data as any);
        reader.on("data", (chunk: Buffer) => {
          controller.enqueue(chunk);
        });
        reader.on("end", () => {
          controller.close();
        });
        reader.on("error", (err: Error) => {
          controller.error(err);
        });
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: any) {
    console.error("Chat proxy error:", error);
    return NextResponse.json(
      { error: error.message, details: error.response?.data },
      { status: 500 }
    );
  }
}
