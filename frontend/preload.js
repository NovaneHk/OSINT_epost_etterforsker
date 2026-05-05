// preload.js - runs before any module loads
// Comprehensive polyfill for browser-specific globals in Node.js environment

const fs = require('fs');
const path = require('path');

// Polyfill globals
if (typeof global !== 'undefined') {
  if (typeof global.self === 'undefined') {
    global.self = global;
  }
  if (typeof global.window === 'undefined') {
    global.window = global;
  }
  if (typeof global.document === 'undefined') {
    global.document = {
      querySelector: () => null,
      querySelectorAll: () => [],
      getElementById: () => null,
      getElementsByTagName: () => [],
      getElementsByClassName: () => [],
      createElement: () => ({
        setAttribute: () => {},
        getAttribute: () => null,
        removeAttribute: () => {},
        appendChild: () => {},
        removeChild: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        style: {},
        classList: {
          add: () => {},
          remove: () => {},
          contains: () => false,
          toggle: () => {}
        }
      }),
      createTextNode: () => ({}),
      head: {
        appendChild: () => {},
        removeChild: () => {},
        children: []
      },
      body: {
        appendChild: () => {},
        removeChild: () => {},
        children: []
      },
      addEventListener: () => {},
      removeEventListener: () => {},
    };
  }
  // Polyfill webpack chunk array
  if (typeof global.webpackChunk_N_E === 'undefined') {
    global.webpackChunk_N_E = [];
  }
  
  // Polyfill React globals for server-side rendering
  if (typeof global.React === 'undefined') {
    try {
      global.React = require('react');
    } catch (e) {
      console.error('[PRELOAD] Could not require react:', e.message);
    }
  }
  if (typeof global.ReactDOM === 'undefined') {
    try {
      global.ReactDOM = require('react-dom');
    } catch (e) {
      console.error('[PRELOAD] Could not require react-dom:', e.message);
    }
  }
}

if (typeof globalThis !== 'undefined') {
  if (typeof globalThis.self === 'undefined') {
    globalThis.self = globalThis;
  }
  if (typeof globalThis.window === 'undefined') {
    globalThis.window = globalThis;
  }
  if (typeof globalThis.document === 'undefined') {
    globalThis.document = global.document;
  }
}

console.log('[PRELOAD] Polyfills applied - self:', typeof self, 'window:', typeof window);

// Ensure React is available globally for server-side compilation
try {
  const React = require('react');
  if (React && React.createContext) {
    global.React = React;
    console.log('[PRELOAD] React loaded successfully with createContext');
  }
} catch (e) {
  console.error('[PRELOAD] Failed to load React:', e.message);
}

// Hook into module loading to patch vendor.js on the fly
const Module = require('module');
const originalRequire = Module.prototype.require;

Module.prototype.require = function(id) {
  const module = originalRequire.apply(this, arguments);
  
  // If this is the first time vendor.js is loaded, patch it
  if (id.includes('vendor.js') && this.filename && this.filename.includes('.next')) {
    const vendorPath = path.resolve(path.dirname(this.filename), id);
    if (fs.existsSync(vendorPath)) {
      try {
        let content = fs.readFileSync(vendorPath, 'utf-8');
        
        // Replace self.webpackChunk with a safe version
        if (content.includes('self.webpackChunk')) {
          content = content.replace(
            /\(self\.webpackChunk/g,
            '((typeof self !== "undefined" ? self : globalThis).webpackChunk'
          );
          fs.writeFileSync(vendorPath, content, 'utf-8');
          console.log('[PRELOAD] Patched vendor.js successfully!');
          
          // Clear require cache and reload
          delete require.cache[vendorPath];
        }
      } catch (err) {
        console.error('[PRELOAD] Failed to patch vendor.js:', err.message);
      }
    }
  }
  
  return module;
};
