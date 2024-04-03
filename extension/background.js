// background.js
let currentTab;

let urlHash = '';
let captchaUrl = '';

let imageUrls = [];

// on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});

let state = 'idle';

// on tab load complete
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // on initiate, store tabId in currentTab
    if (changeInfo.status === 'loading' && tab.url.match(/^https?:\/\/.*/)) {
        currentTab = tabId;
    }
    // check if tab url is https?://.*
    if (changeInfo.status === 'complete' && tab.url.match(/^https?:\/\/.*/)) {
        // check if the tab is not already in the frameIds
        if(captchaUrl != '' && imageUrls.length == 0 && state === 'idle') {
            sendToApi('completed');
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
        if(details.url.includes('&t=bv&')) {
            // call localhost:8001/v1/response with the hash from chrome.storage.session;
            sendToApi("blocked");
        }
        // save image urls in the global variable if ends with .png or .jpg
        if (details.url.endsWith('.png') || details.url.endsWith('.jpg')) {
            imageUrls.push(details.url);
        }
        console.log('Request started: ', details.url);
    },
    { urls: ["<all_urls>"] }
);

function retryAndCallApi(hash, currentUrl) {
    // clear cookies with name `datadome`
    chrome.cookies.getAll({url: captchaUrl}, function(cookies) {
        let datadomeCookie = cookies.find(cookie => cookie.name === 'datadome');
        chrome.cookies.remove({url: captchaUrl, name: 'datadome'}, function() {
            console.log('Cookie removed: ', datadomeCookie);
        });
        // check if hashTimeout is set
        chrome.storage.session.get(['hashTimeout']).then((data) => {
            console.log('HashTimeout: ', data.hashTimeout);
            let hashTimeout = data.hashTimeout || 0;
            if (hashTimeout > 1) {
                chrome.storage.session.set({hashTimeout: hashTimeout + 1});
                setTimeout(() => {
                    callToApi(hash, currentUrl, currentUrl);
                }, 1000);
                return;
            } else {
                chrome.storage.session.set({hashTimeout: 1});
            }
            // open new tab with the captchaUrl
            chrome.tabs.create({url: captchaUrl});
                // close the current tab
            if (currentTab)
                chrome.tabs.remove(currentTab);
        });
    });    
}

function callToApi(hash, currentUrl, data){
    fetch('http://localhost:8001/v1/response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({hashedUrl: hash, url: currentUrl, body: data})
    })
}

function sendToApi(currentUrl){
    chrome.storage.session.get(['hash']).then((data) => {
        let hash = data.hash || urlHash;
        console.log('Hash: ', hash);
        if (currentUrl.includes('/captcha/check'))
            fetch(currentUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                callToApi(hash, currentUrl, data);
            }).catch(error => {
                console.error('Error sending response to API: ', error);
            });
        else if(currentUrl == 'blocked')
            retryAndCallApi(hash, currentUrl);
        else {
            // get cookie for datadome
            chrome.cookies.getAll({url: captchaUrl}, function(cookies) {
                let datadomeCookie = cookies.find(cookie => cookie.name === 'datadome');
                callToApi(hash, captchaUrl, {
                    cookie: 'datadome=' + datadomeCookie.value + ';'
                });
            });
        }
    });
}

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
            // call localhost:8001/v1/response with the hash from chrome.storage.session;
            sendToApi(details.url);
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
            solvePuzzle(bgImageUrl, pieceImageUrl);
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
function solvePuzzle(bgImageUrl, pieceImageUrl, retries = 0) {
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
        if (retries < 3) {
            console.log('Retrying to solve puzzle');
            solvePuzzle(bgImageUrl, pieceImageUrl, retries + 1);
        }
        else {
            sendToApi('blocked');
        }
    });
}


// get message from index.html 
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
    console.log('Message received: ', request);
    if (request.message === 'storeHash') {
        chrome.storage.session.set({hash: request.hash});
        urlHash = request.hash;
        captchaUrl = request.url;
        // close the tab
        // open new tab with the captchaUrl
        chrome.tabs.create({url: captchaUrl});
        // close the current tab
        chrome.tabs.remove(sender.tab.id);
    }
    return true;
});