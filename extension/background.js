// background.js
let currentTab;
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {

  if (changeInfo.status === 'complete' && /^https?:/.test(tab.url)) {
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


// on request from Tab and it's iframes
chrome.webRequest.onCompleted.addListener(
    function(details) {
        if (details.initiator && details.initiator.includes('chrome-extension')) {
            return;
        }
        if (!details.url.includes('captcha-delivery.com')) {
            return;
        }
        currentTab = details.tabId;
        chrome.debugger.attach({ 
            tabId: currentTab
        }, "1.0", onAttach.bind(null, currentTab));
        console.log('Request completed: ', details.url);
        if (details.url.includes('https://geo.captcha-delivery.com/captcha/?initialCid')) {
            solveCaptcha(currentTab);
        }
    },
    { urls: ["<all_urls>"], types: ["xmlhttprequest"] }
);


function onAttach(tabId) {

    chrome.debugger.sendCommand({ //first enable the Network
        tabId: tabId
    }, "Network.enable");
    chrome.debugger.onEvent.addListener(allEventHandler);

}


function allEventHandler(debuggeeId, message, params) {
    console.log('Event: ', message);
    if (currentTab != debuggeeId.tabId) {
        return;
    }

    if (message == "Network.responseReceived") { 
        chrome.debugger.sendCommand({
            tabId: debuggeeId.tabId
        }, "Network.getResponseBody", {
            "requestId": params.requestId
        }, function(response) {
            console.log(response);
            chrome.debugger.detach(debuggeeId);
        });
    }

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