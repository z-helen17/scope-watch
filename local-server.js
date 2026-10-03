const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

for (const line of fs.readFileSync(path.join(__dirname, '.env.local'), 'utf8').split(/\r?\n/)) {
  const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (match && match[2]) process.env[match[1]] = match[2].trim();
}

const run = require('./api/run');
const publicDir = path.join(__dirname, 'public');

const port = Number(process.env.PORT || 3000);

http.createServer(async (req, res) => {
  if (req.url === '/api/run') {
    res.status = (code) => ({ json: (body) => {
      res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(body));
    }});
    return run(req, res);
  }
  const requested = req.url === '/' ? 'index.html' : decodeURIComponent(req.url).replace(/^\/+/, '');
  const file = path.resolve(publicDir, requested);
  if (!file.startsWith(publicDir) || !fs.existsSync(file)) { res.writeHead(404); return res.end('Not found'); }
  const type = file.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': type });
  fs.createReadStream(file).pipe(res);
}).listen(port, () => console.log(`Scope Watch is running at http://localhost:${port}`));
