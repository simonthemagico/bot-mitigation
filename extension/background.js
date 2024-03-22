// background.js
let currentTab;
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {

  if (changeInfo.status === 'complete' && /^https?:/.test(tab.url)) {
        if (new URL(tab.url).hostname === 'leboncoin.fr') {
            attachDebugger(tab.id);
        }
      chrome.scripting.executeScript({
          target: {tabId: tabId, allFrames: true},
          files: ['content.js']
      }).then(() => {
          console.log('Script injected successfully');
      }).catch(error => console.error('Error injecting script:', error));
  }
});


// on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});

// on request start, attach debugger

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        if (details.initiator && details.initiator.includes('chrome-extension')) {
            return;
        }
        if (!details.url.includes('captcha-delivery.com')) {
            return;
        }
        console.log('Request started: ', details.url);
        if (details.url.includes('https://geo.captcha-delivery.com/captcha/check')) {
            
        }
    },
    { urls: ["<all_urls>"], types: ["xmlhttprequest"] }
);


// on request from Tab and it's iframes
chrome.webRequest.onCompleted.addListener(
    function(details) {
        if (details.initiator && details.initiator.includes('chrome-extension')) {
            return;
        }
        if (!details.url.includes('captcha-delivery.com')) {
            return;
        }
        console.log('Request completed: ', details.url);
        if (details.url.includes('https://geo.captcha-delivery.com/captcha/?initialCid')) {
            solveCaptcha(currentTab);
        }
    },
    { urls: ["<all_urls>"], types: ["xmlhttprequest"] }
);


function attachDebugger(tabId) {
    chrome.debugger.attach({ tabId: tabId }, '1.3', function() {
        if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError.message);
            return;
        }

        chrome.debugger.sendCommand({ tabId: tabId }, 'Network.enable');

        chrome.debugger.onEvent.addListener((source, method, params) => {
            if (source.tabId === tabId && method === 'Network.responseReceived') {
                const requestUrl = params.response.url;
                console.log('Response received:', requestUrl);
                // Check if the URL ends with '/captcha/check'
                if (requestUrl.endsWith('/captcha/check')) {
                    // Fetch the response body
                    chrome.debugger.sendCommand(
                        { tabId: tabId },
                        'Network.getResponseBody',
                        { requestId: params.requestId },
                        (response) => {
                            if (!response.body) return; // No response body
                            console.log('Captcha check response:', response.body);
                            // Here you can send the response body to your extension's frontend or handle it as needed
                        }
                    );
                }
            }
        });
    });
}


// get cookies from the response
function getCookies(response) {
    console.log('Response: ', response);    
}

// solve captcha
function solveCaptcha(tabId) {
    chrome.scripting.executeScript({
        target: { tabId },
        function: () => Array.from(document.querySelectorAll('link[rel="preload"]')).map(link => link.href)
    }, async (results) => { 
        console.log(results);
        let imageUrls = results[0].result;
        console.log('Preload image URLs:', imageUrls);

        let bgImageUrl = imageUrls.find(url => !url.includes('.frag.'));
        let pieceImageUrl = imageUrls.find(url => url.includes('.frag.'));
        solvePuzzle(bgImageUrl, pieceImageUrl, tabId);
        
    });
}

// solve puzzle
function solvePuzzle(bgImageUrl, pieceImageUrl, tabId) {
    const url = `https://captcha.riseofninja.com/api/v1/puzzleSolver`;
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            bgImageUrl,
            pieceImageUrl
        })
    })
    .then(response =>  response.json())
    .then(data => {
        chrome.tabs.sendMessage(tabId, {action: "slideSlider", xCoord: data.x});

    })
    .catch(error => {
        console.error('Error sending response to API: ', error);
    });
}