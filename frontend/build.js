#!/usr/bin/env node

// Monkey-patch Module._compile to inject self polyfill into vendor.js
const Module = require('module');
const originalCompile = Module.prototype._compile;

Module.prototype._compile = function(content, filename) {
  // If this is vendor.js, inject the polyfill at the top
  if (filename.includes('vendor.js') && filename.includes('.next')) {
    console.log(`[BUILD WRAPPER] Patching ${filename}...`);
    content = `
      // Polyfill for 'self' in Node.js environment
      if (typeof self === 'undefined') {
        globalThis.self = globalThis;
      }
    ` + content;
  }
  
  return originalCompile.call(this, content, filename);
};

// Set global.self as fallback
if (typeof global !== 'undefined' && typeof global.self === 'undefined') {
  global.self = global;
  globalThis.self = globalThis;
  console.log('[BUILD WRAPPER] Set global.self = global');
}

// Now run Next.js build
const { spawn } = require('child_process');

const build = spawn('next', ['build'], {
  stdio: 'inherit',
  shell: true
});

build.on('close', (code) => {
  if (code === 0) {
    console.log('\n[BUILD WRAPPER] Build completed successfully!');
  } else {
    console.error(`\n[BUILD WRAPPER] Build failed with code ${code}`);
  }
  process.exit(code);
});
