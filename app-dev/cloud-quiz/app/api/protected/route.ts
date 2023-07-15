import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const user = await getAuthenticatedUser(request);
  if(user.uid) {
    return NextResponse.json({ text: 'hello, this is a protected route, you must be authenticated!' }, { status: 200 })
  } else {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'authentication failed' }),
      { status: 401, headers: { 'content-type': 'application/json' } }
    )
  }
}

export async function POST(request: NextRequest, response: NextResponse) {
  const user = await getAuthenticatedUser(request);
  if(user.uid) {
    return NextResponse.json({ text: 'hello, this is a protected route, you must be authenticated!' }, { status: 200 })
  } else {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'authentication failed' }),
      { status: 401, headers: { 'content-type': 'application/json' } }
    )
  }
}