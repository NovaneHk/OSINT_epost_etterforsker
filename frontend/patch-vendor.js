const fs = require('fs');
const path = require('path');

// Patch vendor.js to replace 'self' with 'globalThis'
const vendorPath = path.join(__dirname, '.next', 'server', 'vendor.js');

if (fs.existsSync(vendorPath)) {
  console.log('[PATCH] Patching vendor.js to replace self with globalThis...');
  
  let content = fs.readFileSync(vendorPath, 'utf-8');
  
  // Replace self references with globalThis
  content = content.replace(
    '(self.webpackChunk_N_E=self.webpackChunk_N_E||[])',
    '((typeof self !== "undefined" ? self : globalThis).webpackChunk_N_E=(typeof self !== "undefined" ? self : globalThis).webpackChunk_N_E||[])'
  );
  
  fs.writeFileSync(vendorPath, content, 'utf-8');
  console.log('[PATCH] vendor.js patched successfully!');
} else {
  console.log('[PATCH] vendor.js not found, skipping patch');
}
