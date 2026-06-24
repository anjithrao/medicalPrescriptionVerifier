import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const dist = join(root, 'dist');
const templates = join(root, 'templates');
const staticAssets = join(root, 'static', 'assets');

if (!existsSync(dist)) {
  throw new Error('dist folder does not exist. Run vite build first.');
}

mkdirSync(templates, { recursive: true });
mkdirSync(join(root, 'static'), { recursive: true });
copyFileSync(join(dist, 'index.html'), join(templates, 'index.html'));

if (existsSync(staticAssets)) {
  rmSync(staticAssets, { recursive: true, force: true });
}
cpSync(join(dist, 'assets'), staticAssets, { recursive: true });

console.log('Copied dist/index.html to templates/index.html and dist/assets to static/assets.');
