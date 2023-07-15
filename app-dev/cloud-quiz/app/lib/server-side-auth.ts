import { NextRequest } from "next/server";
import { getAuth } from 'firebase-admin/auth';
import { initializeApp } from 'firebase-admin/app';

export const app = initializeApp();

export async function getAuthenticatedUser(request: NextRequest) {
  const token = request.headers.get('Authorization') || '';
  const decodedToken = await getAuth().verifyIdToken(token);
  return decodedToken;
};

export async function isAuthenticated(request: NextRequest) {
  const authUser = await getAuthenticatedUser(request);
  if (authUser.uid) {
    return true;
  }
  return false;
};