import { NextResponse } from "next/server";

// Liveness probe for the Docker HEALTHCHECK (apps/web/Dockerfile) and any
// load balancer/orchestrator checks. Intentionally has no dependencies —
// it should reflect only "is this Next.js server process up".
export function GET() {
  return NextResponse.json({ status: "ok" });
}
