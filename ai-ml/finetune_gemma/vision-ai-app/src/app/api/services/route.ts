import { NextResponse } from "next/server";
import { ServicesClient } from "@google-cloud/run";
import { GoogleAuth } from "google-auth-library";

export async function GET() {
  try {
    const auth = new GoogleAuth({
      scopes: "https://www.googleapis.com/auth/cloud-platform",
    });
    const projectId = await auth.getProjectId();
    const client = new ServicesClient();

    const [services] = await client.listServices({
      parent: `projects/${projectId}/locations/-`,
    });

    // Just return the metadata quickly
    const results = services.map((service) => ({
      name: service.name?.split("/").pop(),
      url: service.uri,
      location: service.name?.split("/")[3],
      models: [], // Will be filled by individual probes
    }));

    return NextResponse.json(results);
  } catch (error: any) {
    console.error("Error listing services:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
