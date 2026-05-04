export const dynamic = "force-dynamic";

const DEFAULT_PROXY_TARGET = "http://localhost:8000";
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function getProxyTarget(): string {
  return process.env.PINKY_WEB_API_PROXY_TARGET?.replace(/\/$/, "") ?? DEFAULT_PROXY_TARGET;
}

function buildTargetUrl(request: Request): URL {
  const incoming = new URL(request.url);
  const target = new URL(getProxyTarget());
  const proxiedPath = incoming.pathname.replace(/^\/api\/?/, "");
  const basePath = target.pathname.replace(/\/$/, "");
  target.pathname = `${basePath}/api/${proxiedPath}`.replace(/\/+/g, "/");
  target.search = incoming.search;
  return target;
}

async function proxyRequest(request: Request): Promise<Response> {
  const targetUrl = buildTargetUrl(request);
  const headers = new Headers(request.headers);

  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
    signal: AbortSignal.timeout(30_000),
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(targetUrl, init);
    const responseHeaders = new Headers(upstream.headers);

    for (const header of HOP_BY_HOP_HEADERS) {
      responseHeaders.delete(header);
    }

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      {
        error: {
          code: "proxy_unavailable",
          message: "API proxy target unavailable",
        },
      },
      { status: 502 },
    );
  }
}

export async function GET(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function POST(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function PUT(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function PATCH(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function DELETE(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function OPTIONS(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function HEAD(request: Request): Promise<Response> {
  return proxyRequest(request);
}
