const REPOSITORY_ROOT = "https://raw.githubusercontent.com/pkpardeepkumar30/news/main";

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function publicPath(pathname) {
  if (pathname === "/" || pathname === "/index.html") return "/index.html";
  if (pathname === "/app.js" || pathname === "/styles.css" || pathname === "/data/news.json") return pathname;
  if (pathname.startsWith("/assets/") || pathname.startsWith("/data/archive/")) return pathname;
  return null;
}

function contentType(pathname) {
  const extension = Object.keys(CONTENT_TYPES).find((item) => pathname.endsWith(item));
  return extension ? CONTENT_TYPES[extension] : "application/octet-stream";
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {status: 405, headers: {Allow: "GET, HEAD"}});
    }

    const requestUrl = new URL(request.url);
    const pathname = publicPath(requestUrl.pathname);
    if (!pathname) {
      return new Response("Not found", {
        status: 404,
        headers: {"Content-Type": "text/plain; charset=utf-8", "X-Content-Type-Options": "nosniff"},
      });
    }

    try {
      const isLiveData = pathname === "/data/news.json" || pathname.startsWith("/data/archive/");
      const upstream = await fetch(`${REPOSITORY_ROOT}${pathname}`, {
        method: request.method,
        cf: {cacheEverything: true, cacheTtl: isLiveData ? 60 : 300},
      });
      if (!upstream.ok) return env.ASSETS.fetch(request);

      const headers = new Headers(upstream.headers);
      headers.set("Content-Type", contentType(pathname));
      headers.set("Cache-Control", isLiveData ? "public, max-age=30" : "public, max-age=300");
      headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
      headers.set("X-Content-Type-Options", "nosniff");
      headers.delete("Set-Cookie");
      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers,
      });
    } catch {
      return env.ASSETS.fetch(request);
    }
  },
};
