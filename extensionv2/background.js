// background.js
let currentTab;
let imageUrls = [];
let apiPort = 8000;
let state = 'idle';


// on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});


// on tab load complete
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // on initiate, store tabId in currentTab
    if (changeInfo.status === 'loading' && tab.url.match(/^https?:\/\/.*/)) {
        currentTab = tabId;
        state = 'idle';
        imageUrls = [];
        console.log('Tab loading: ', tab.url);
    }
    // if completed solvePuzzle
    if (changeInfo.status === 'complete' && tab.url.match(/^https?:\/\/.*/)) {
        console.log('Tab loaded: ', tab.url);
        if (imageUrls.length === 2 && state === 'idle') {
            state = 'processing';
            console.log('Image urls: ', imageUrls);
            let bgImageUrl = imageUrls.find(url => !url.includes('.frag.'));
            let pieceImageUrl = imageUrls.find(url => url.includes('.frag.'));
            solvePuzzle(bgImageUrl, pieceImageUrl);
        }
        else if(!tab.url.includes('localhost')){
            chrome.cookies.getAll({url: tab.url}, function(cookies) {
                // set cookies in a query string
                let cookieDict = '';
                let is_valid_cookie = true;
                cookies.forEach(cookie => {
                    is_valid_cookie = !(cookieDict == '' && cookie.name == 'datadome')
                    cookieDict += `${cookie.name}=${cookie.value};`;
                });
                // if more than one cookie
                // send cookies to API
                is_valid_cookie && sendToApi(cookieDict);
            });
        }
    }
});

chrome.webRequest.onBeforeRequest.addListener(
    function(details) {
        if (details.initiator && details.initiator.includes('chrome-extension')) {
            return;
        }
        if (!details.url.includes('captcha-delivery.com')) {
            return;
        }
        console.log('Request started: ', details.url);
        if(details.url.includes('&t=bv&'))
            return sendToApi("blocked");
        if (details.url.includes('/interstitial/'))
            state = 'interstitial';
            // get request body
        if (details.url == 'https://geo.captcha-delivery.com/interstitial/') {
            try{
                apiPort = 8000;
                let requestBody = details.requestBody;
                if (requestBody.raw) {
                    let decodedString = String.fromCharCode.apply(
                        null,
                        new Uint8Array(requestBody.raw[0].bytes)
                    );
                    sendToApi(decodedString);
                }
                if (requestBody.formData) {
                    let formData = requestBody.formData;
                    let payload = '';
                    for (let key in formData) {
                        payload += key + '=' + formData[key] + '&';
                    }
                    sendToApi(payload);
                }
            } catch (error) {
                console.error('Error getting request body: ', error);
            }
            console.log('Interstitial Captcha: ', details.url);
        }
        if (details.url.includes('/captcha/check')) {
            state = 'idle';
            imageUrls = [];
            sendToApi(details.url);
        }
        // save image urls in the global variable if ends with .png or .jpg
        if (details.url.endsWith('.png') || details.url.endsWith('.jpg')) {
            imageUrls.push(details.url);
        }
    },
    { urls: ["<all_urls>"] },
    ["requestBody"]
);

function callToApi(hash, currentUrl, response){
    chrome.storage.session.get(['apiPort']).then((data) => {
        apiPort = data.apiPort || apiPort;
        fetch(`http://localhost:${apiPort}/v1/response`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({hashedUrl: hash, url: currentUrl, body: response})
        })
    });
}

function sendToApi(payload){
    chrome.tabs.query({
        active: true,
        currentWindow: true
    }, function(tabs) {
        let webUrl = tabs[0].url;
        // get hash from webUrl params
        let params = new URLSearchParams(webUrl.split('?')[1]);
        let hash = params.get('cid');
        // get hash from localStorage
        chrome.storage.session.get(['hash'], function(data) {
            hash = data.hash || hash;
            callToApi(hash, webUrl, {payload});
        });
    });
    
}

function sendMessage(message) {
   // execute content.js script
   // and then send message
   chrome.scripting.executeScript({
        target: { allFrames: true, tabId: currentTab },
        files: ['content.js']
    }).then(() => {
        console.log('Script executed');
        chrome.tabs.sendMessage(currentTab, message);
    });
}

// solve puzzle
function solvePuzzle(bgImageUrl, pieceImageUrl, retries = 0) {
    console.log('Solving puzzle with bgImageUrl: ', bgImageUrl, ' and pieceImageUrl: ', pieceImageUrl);
    const url = `http://localhost:8015/api/v1/puzzleSolver`;
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
        sendMessage({action: "slideSlider", xCoord: data.x});
    })
    .catch(error => {
        console.error('Error sending response to API: ', error);
        // log full exception
        if (retries < 3) {
            console.log('Retrying to solve puzzle');
            solvePuzzle(bgImageUrl, pieceImageUrl, retries + 1);
        }
        else {
            console.log("Blocked");
            sendToApi('blocked');
        }
    });
}


// on message from content.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received: ', request);
    if (request.action === 'slideSlider') {
        sendToApi('blocked');
    }
    return true;
});

// listen for messages from website
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
    console.log('Message received: ', request);
    if (request.message === 'store') {
        chrome.storage.session.set({hash: request.hash}, function() {
            console.log('Hash stored: ', request.hash);
        });
    }
    return true;
});