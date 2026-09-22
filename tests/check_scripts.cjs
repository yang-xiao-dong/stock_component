// 仅检查语法，不启动浏览器或执行界面交互。
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
new Function(fs.readFileSync(path.join(root, 'assets/shared.js'), 'utf8'));
const files = ['assets/shell.html'];
for (const component of fs.readdirSync(path.join(root, 'components'), { withFileTypes: true })) {
  if (!component.isDirectory()) continue;
  const file = `components/${component.name}/ui.html`;
  if (fs.existsSync(path.join(root, file))) files.push(file);
}
for (const file of files) {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
    new Function(match[1]);
  }
}
console.log(`脚本语法检查通过：shared.js + ${files.length} 个页面`);
