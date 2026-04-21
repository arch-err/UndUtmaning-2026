// file-server.ts
//
// deno run -ENR file-server.ts

const BASE_DIR = Deno.env.get("BASE_DIR");

function sanitize(path: string) {
  return path.replaceAll(/^\.\./g, "");
}

Deno.serve(
  { port: 8080 },
  async (request) => {
    try {
      const url = new URL(request.url);
      const path = sanitize(url.searchParams.get("path") || "");
      switch (url.pathname) {
        case "/": {
          return new Response("Piscis Cerebrum - Sprechen sie fish?");
        }
        case "/list-dir": {
          let fileList = "";
          for await (const f of Deno.readDir(`${BASE_DIR}/${path}`)) {
            if (!f.isFile) continue;
            fileList = `${fileList}\n${f.name}`;
          }
          return new Response(fileList);
        }
        case "/read-file": {
          const file = await Deno.open(`${BASE_DIR}/${path}`, { read: true });
          return new Response(file.readable, {
            headers: {
              "content-type": "text/plain; charset=utf-8",
            },
          });
        }
        default:
          return new Response("404 Not Found", { status: 404 });
      }
    } catch {
      return new Response("404 Not Found", { status: 404 });
    }
  },
);
