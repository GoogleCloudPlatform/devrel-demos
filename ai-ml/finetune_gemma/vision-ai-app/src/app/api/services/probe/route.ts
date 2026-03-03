import { NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export async function POST(req: Request) {
  try {
    const { url } = await req.json();
    const auth = new GoogleAuth();
    const idTokenClient = await auth.getIdTokenClient(url);
    
    // vLLM / OpenAI compatible endpoint
    const response = await idTokenClient.request({
      url: `${url.replace(/\/$/, "")}/v1/models`,
      timeout: 10000, // 10s timeout to avoid hanging on slow/non-vLLM services
    }) as any;
    
    let models: string[] = [];
    if (response.data && Array.isArray(response.data.data)) {
      models = response.data.data.map((m: any) => m.id);
    }

    return NextResponse.json({ models });
  } catch (error: any) {
    // If it fails, it's likely not a vLLM service or it's currently unavailable
    console.log(`Probe failed for ${error.message}`);
    return NextResponse.json({ models: [], error: "Not a valid vLLM service or unavailable" });
  }
}
