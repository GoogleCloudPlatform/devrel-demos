import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ text: 'hello' }, { status: 200 })
}