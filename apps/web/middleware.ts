import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/tasks", "/watch", "/history", "/alerts", "/settings"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get("pinky_session");

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (isProtected && !session) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (pathname === "/login" && session) {
    const tasksUrl = new URL("/tasks", request.url);
    return NextResponse.redirect(tasksUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/tasks/:path*", "/watch/:path*", "/history/:path*", "/alerts/:path*", "/settings/:path*", "/login"],
};
