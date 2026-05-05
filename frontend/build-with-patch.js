const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('[BUILD] Starting patched Next.js build...');

// Run next build
const buildProcess = spawn('next', ['build'], {
  stdio: ['inherit', 'pipe', 'pipe'],
  shell: true,
});

let buildOutput = '';
let errorOutput = '';

buildProcess.stdout.on('data', (data) => {
  const text = data.toString();
  buildOutput += text;
  process.stdout.write(text);
  
  // Check if compilation finished successfully
  if (text.includes('Compiled successfully')) {
    console.log('\n[BUILD] Compilation finished, applying vendor.js patch...');
    
    // Apply the patch
    const vendorPath = path.join(__dirname, '.next', 'server', 'vendor.js');
    if (fs.existsSync(vendorPath)) {
      try {
        let content = fs.readFileSync(vendorPath, 'utf-8');
        const original = content;
        
        // Replace all self references with safe fallback
        content = content.replace(
          /(^|[^a-zA-Z0-9_])self([^a-zA-Z0-9_])/g,
          '$1(typeof self !== "undefined" ? self : globalThis)$2'
        );
        
        if (content !== original) {
          fs.writeFileSync(vendorPath, content, 'utf-8');
          console.log('[BUILD] ✓ vendor.js patched successfully!');
        } else {
          console.log('[BUILD] No self references found in vendor.js');
        }
      } catch (err) {
        console.error('[BUILD] Failed to patch vendor.js:', err.message);
      }
    }
  }
});

buildProcess.stderr.on('data', (data) => {
  const text = data.toString();
  errorOutput += text;
  process.stderr.write(text);
});

buildProcess.on('close', (code) => {
  if (code === 0) {
    console.log('[BUILD] Build completed successfully!');
  } else {
    console.error(`[BUILD] Build failed with code ${code}`);
  }
  process.exit(code);
});
