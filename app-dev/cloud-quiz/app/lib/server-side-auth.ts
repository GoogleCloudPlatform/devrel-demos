import { NextRequest, NextResponse } from "next/server";
import { getAuth, DecodedIdToken } from 'firebase-admin/auth';
import { app } from "@/app/lib/firebase-server-initialization";

export async function getAuthenticatedUser(request: NextRequest): Promise<DecodedIdToken> {
  const token = request.headers.get('Authorization') || '';
  const decodedIdToken = await getAuth(app).verifyIdToken(token);
  return decodedIdToken;
};