/**
 * upload.js — Extra drag & drop helpers
 * (Most logic is in main.js; this handles edge cases)
 */

// Prevent browser default drag behavior across the whole page
document.addEventListener('dragover',  e => e.preventDefault());
document.addEventListener('drop',      e => e.preventDefault());