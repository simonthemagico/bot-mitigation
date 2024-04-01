// background.js
let currentTab;

let imageUrls = [];

// on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});

let state = 'idle';

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        if (details.initiator && details.initiator.includes('chrome-extension')) {
            return;
        }
        if (!details.url.includes('captcha-delivery.com')) {
            return;
        }
        // save image urls in the global variable if ends with .png or .jpg
        if (details.url.endsWith('.png') || details.url.endsWith('.jpg')) {
            imageUrls.push(details.url);
        }
        console.log('Request started: ', details.url);
    },
    { urls: ["<all_urls>"] }
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
        if (details.url.includes('/captcha/check')) {
            // call localhost:8001/v1/response with the hash from sessionStorage
            hash = sessionStorage.getItem('hash');
            fetch('http://localhost:8001/v1/response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({hashedUrl: hash, url: details.url})
            })
            state = 'idle';
            imageUrls = [];
            frameIds = [];
        }
        console.log('Request completed: ', details.url);
        if (imageUrls.length === 2 && frameIds.length > 0 && state === 'idle') {
            state = 'processing';
            console.log('Image urls: ', imageUrls);
            let bgImageUrl = imageUrls.find(url => !url.includes('.frag.'));
            let pieceImageUrl = imageUrls.find(url => url.includes('.frag.'));
            solvePuzzle(bgImageUrl, pieceImageUrl, details.tabId);
        }
    },
    { urls: ["<all_urls>"]}
);


let frameIds = []; // Store frameIds of interest

chrome.webNavigation.onCommitted.addListener(details => {
    if (details.frameId !== 0 && details.url.includes("captcha-delivery.com")) {
        currentTab = details.tabId;
        // Assuming iframes loading captcha-delivery.com content are of interest
        frameIds.push({ tabId: details.tabId, frameId: details.frameId });
    }
}, { url: [{ urlMatches: 'captcha-delivery.com' }] });
// get cookies from the response
function getCookies(response) {
    console.log('Response: ', response);    
}
function sendMessageToIframe(action, xCoord) {
   // execute content.js script in all iframes
   // and then send message to the iframe
   chrome.scripting.executeScript({
        target: { allFrames: true, tabId: currentTab },
        files: ['content.js']
    }).then(() => {
        console.log('Script executed in all frames');
        frameIds.forEach(frame => {
            chrome.tabs.sendMessage(frame.tabId, {action, xCoord}, {frameId: frame.frameId});
        });
    });
}

// solve puzzle
function solvePuzzle(bgImageUrl, pieceImageUrl, tabId) {
    console.log('Solving puzzle with bgImageUrl: ', bgImageUrl, ' and pieceImageUrl: ', pieceImageUrl);
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
        console.log('Response from API: ', data);
        sendMessageToIframe("slideSlider", data.x);

    })
    .catch(error => {
        console.error('Error sending response to API: ', error);
    });
}