
(function() {
    window.postMessage({ type: "FROM_EXTENSION", extensionId: chrome.runtime.id }, "*");
})();