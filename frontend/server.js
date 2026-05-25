const http = require('http');
const fs = require('fs');
const path = require('path');

const dir = 'C:\\Users\\houhuixin\\Desktop\\企业知识库部署\\frontend';
const port = 3000;

http.createServer((req, res) => {
  let filePath = path.join(dir, req.url === '/' ? 'index.html' : req.url);
  const ext = path.extname(filePath);
  const mime = { '.html':'text/html;charset=utf-8', '.js':'application/javascript', '.css':'text/css', '.png':'image/png', '.jpg':'image/jpeg', '.svg':'image/svg+xml', '.json':'application/json' };
  
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not Found');
      return;
    }
    res.writeHead(200, {
      'Content-Type': mime[ext] || 'text/plain',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    });
    res.end(data);
  });
}).listen(port, () => {
  console.log(`Frontend server running at http://localhost:${port}/`);
});
