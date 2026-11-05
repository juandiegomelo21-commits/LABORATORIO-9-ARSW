// Balanceador de carga L4/L7 mínimo que emula al Azure Load Balancer del laboratorio.
//  - Frontend: puerto 80 -> aquí LB_PORT (por defecto 8080)
//  - Backend pool: BACKENDS="VM1=127.0.0.1:3001,VM2=127.0.0.1:3002,..."
//  - Health probe: HTTP GET / cada 5 s; un nodo sale del pool tras 2 fallos seguidos (igual que Azure)
//  - Load balancing rule: reparte en round-robin entre los nodos sanos (Azure usa hash de 5-tupla)
//  - Idle timeout de 4 minutos como el de Azure: si la conexión no recibe datos en 4 min se resetea
// Uso: node balanceador.js   (variables LB_PORT, BACKENDS)
const http = require('http');

const LB_PORT = parseInt(process.env.LB_PORT || '8080', 10);
const PROBE_INTERVAL_MS = 5000;
const UNHEALTHY_THRESHOLD = 2;
const IDLE_TIMEOUT_MS = 4 * 60 * 1000;

const pool = (process.env.BACKENDS || 'VM1=127.0.0.1:3001').split(',').map((b) => {
  const [name, addr] = b.split('=');
  const [host, port] = addr.split(':');
  return { name, host, port: parseInt(port, 10), healthy: true, fails: 0, enviadas: 0, ok: 0, errores: 0 };
});
let rr = 0;

const ts = () => new Date().toISOString().substring(11, 19);

function probe(node) {
  const req = http.get({ host: node.host, port: node.port, path: '/', timeout: PROBE_INTERVAL_MS }, (res) => {
    res.resume();
    if (res.statusCode === 200) {
      if (!node.healthy) console.log(`${ts()} [probe] ${node.name} vuelve a estar SANO`);
      node.healthy = true; node.fails = 0;
    } else fail(node);
  });
  req.on('timeout', () => req.destroy(new Error('timeout')));
  req.on('error', () => fail(node));
}
function fail(node) {
  node.fails++;
  if (node.healthy && node.fails >= UNHEALTHY_THRESHOLD) {
    node.healthy = false;
    console.log(`${ts()} [probe] ${node.name} NO responde al probe -> fuera del pool`);
  }
}
setInterval(() => pool.forEach(probe), PROBE_INTERVAL_MS);

function elegir() {
  let sanos = pool.filter((n) => n.healthy);
  if (sanos.length === 0) sanos = pool; // si todos fallan el probe, se reparte entre todos
  return sanos[rr++ % sanos.length];
}

const server = http.createServer((req, res) => {
  if (req.url === '/lb/status') {
    res.setHeader('Content-Type', 'application/json');
    return res.end(JSON.stringify(pool.map(({ name, port, healthy, enviadas, ok, errores }) =>
      ({ name, port, healthy, enviadas, ok, errores })), null, 2));
  }
  const node = elegir();
  node.enviadas++;
  const t0 = Date.now();
  console.log(`${ts()} ${req.method} ${req.url} -> ${node.name}`);
  const up = http.request({ host: node.host, port: node.port, path: req.url, method: req.method, headers: req.headers }, (r) => {
    res.writeHead(r.statusCode, { ...r.headers, 'x-backend': node.name });
    r.pipe(res);
    r.on('end', () => {
      node.ok++;
      console.log(`${ts()} ${req.url} <- ${node.name} ${r.statusCode} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    });
  });
  up.on('error', (e) => {
    node.errores++;
    console.log(`${ts()} ${req.url} xx ${node.name} ${e.message}`);
    res.destroy();
  });
  req.pipe(up);
});
server.on('connection', (s) => s.setTimeout(IDLE_TIMEOUT_MS, () => s.destroy())); // idle timeout tipo Azure
server.listen(LB_PORT, () =>
  console.log(`Balanceador escuchando en :${LB_PORT} -> pool [${pool.map((n) => `${n.name}@${n.port}`).join(', ')}]`));
