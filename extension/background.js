// PMFBY Claim Assistant - Background Service Worker
// Simple version without problematic APIs

console.log('PMFBY Claim Assistant background service worker loaded');

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('PMFBY Claim Assistant installed successfully');
    }
    
    if (details.reason === 'update') {
        console.log('PMFBY Claim Assistant updated successfully');
    }
});

// Handle messages from popup (optional)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request);
    sendResponse({success: true});
});

// Basic error handling
self.addEventListener('error', (event) => {
    console.error('PMFBY Extension Error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
    console.error('PMFBY Extension Unhandled Promise Rejection:', event.reason);
});