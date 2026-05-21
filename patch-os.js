const os = require('os');
Object.defineProperty(os, 'release', {
  value: () => '6.5.0',
  writable: true,
  configurable: true
});
