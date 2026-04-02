// Polyfill for 'self' in Node.js server environment
// This is needed because some webpack runtime code expects 'self' to exist
if (typeof global !== 'undefined' && typeof global.self === 'undefined') {
  global.self = global;
}
