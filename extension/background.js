// background.js
let currentTab;
let urlHash = '';
let captchaUrl = '';
let imageUrls = [];
let apiPort = 8001;
let frameIds = []; // Store frameIds of interest
let state = 'idle';
let is_sent = false;


// on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});


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
            // check if not home_visit
            chrome.storage.session.get(['home_visit']).then((data) => {
                let home_visit = data.home_visit || false;
                if (home_visit) {
                    // remove storage home_visit and open captchaUrl
                    chrome.storage.session.remove('home_visit');
                    imageUrls = [];
                    frameIds = [];
                    state = 'idle';
                    chrome.tabs.create({url: captchaUrl});
                    chrome.tabs.remove(tab.id);
                }
                else {
                    sendToApi("completed");
                }

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
        if (details.url.includes('/captcha/check') || details.url.includes('/interstitial/'))
            chrome.storage.session.get(['captchaUrl']).then((data) => {
                captchaUrl = data.captchaUrl || captchaUrl || details.url;
            });
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
                    sendToApi(decodedString, true);
                }
                if (requestBody.formData) {
                    let formData = requestBody.formData;
                    let payload = '';
                    for (let key in formData) {
                        payload += key + '=' + formData[key] + '&';
                    }
                    sendToApi(payload, true);
                }
            } catch (error) {
                console.error('Error getting request body: ', error);
            }
            console.log('Interstitial Captcha: ');
        }
        if (details.url.includes('/captcha/check')) {
            let params = new URLSearchParams(details.url);
            urlHash = params.get('cid');
            sendToApi(params, true);
        }
        // save image urls in the global variable if ends with .png or .jpg
        if (details.url.endsWith('.png') || details.url.endsWith('.jpg')) {
            imageUrls.push(details.url);
        }
    },
    { urls: ["<all_urls>"] },
    ["requestBody"]
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
            let hashTimeout = data.hashTimeout || 0;
            console.log('HashTimeout: ', hashTimeout);
            chrome.storage.session.set({hashTimeout: hashTimeout + 1});
            if (hashTimeout > 1) {
                setTimeout(() => {
                    callToApi(hash, currentUrl, currentUrl);
                }, 1000);
                return;
            }
            state = 'idle';
            imageUrls = [];
            frameIds = [];
            // open new tab with the captchaUrl
            chrome.tabs.create({url: captchaUrl});
                // close the current tab
            if (currentTab)
                chrome.tabs.remove(currentTab);
        });
    });    
}

function callToApi(hash, currentUrl, response){
    if (is_sent) return;
    is_sent = true;
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

function sendToApi(currentUrl, is_payload = false){
    chrome.storage.session.get(['hash']).then((data) => {
        let hash = data.hash || urlHash;
        // using regex, find cid=.+& if no hash found
        if (!hash) {
            let hashMatch = currentUrl.match(/cid=.+&/);
            if (hashMatch) {
                hash = hashMatch[0];
                hash = hash.replace('cid=', '');
                hash = hash.replace('&', '');
            }
        }
        console.log('Hash: ', hash);
        console.log('url: ', currentUrl);
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
                console.error('Error getting cookies', error);
            });
        else if(currentUrl == 'blocked')
            retryAndCallApi(hash, currentUrl);
        else {
            // get all cookies from the browser for all sites
            chrome.cookies.getAll({}, function(cookies) {
                const body = {};
                if(!is_payload)
                {
                    let datadomeCookie = cookies.find(cookie => cookie.name === 'datadome' && captchaUrl.includes(cookie.domain));
                    body.cookie = 'datadome=' + datadomeCookie.value + ';';
                    body.cookies = cookies;
                }
                else body.payload = currentUrl;
                callToApi(hash, captchaUrl, body);
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
            state = 'idle';
            imageUrls = [];
            frameIds = [];
            sendToApi(details.url);
        }
        console.log('Request completed: ', details.url);
        if (imageUrls.length === 2 && state === 'idle') {
            state = 'processing';
            console.log('Image urls: ', imageUrls);
            let bgImageUrl = imageUrls.find(url => !url.includes('.frag.'));
            let pieceImageUrl = imageUrls.find(url => url.includes('.frag.'));
            solvePuzzle(bgImageUrl, pieceImageUrl);
        }
    },
    { urls: ["<all_urls>"]}
);


chrome.webNavigation.onCommitted.addListener(details => {
    if (details.frameId !== 0 && details.url.includes("captcha-delivery.com")) {
        currentTab = details.tabId;
        // Assuming iframes loading captcha-delivery.com content are of interest
        frameIds.push({ tabId: details.tabId, frameId: details.frameId });
    }
}, { url: [{ urlMatches: 'captcha-delivery.com' }] });

function sendMessageToIframe(message) {
   // execute content.js script in all iframes
   // and then send message to the iframe
   chrome.scripting.executeScript({
        target: { allFrames: true, tabId: currentTab },
        files: ['content.js']
    }).then(() => {
        console.log('Script executed in all frames');
        try {
            chrome.tabs.sendMessage(currentTab, message);
        }catch (error) {}
        frameIds.forEach(frame => {
            chrome.tabs.sendMessage(frame.tabId, message, {frameId: frame.frameId});
        });
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
        sendMessageToIframe({action: "slideSlider", xCoord: data.x});
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


// get message from index.html 
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
    console.log('Message received: ', request);
    if (request.message === 'storeHash') {
        chrome.storage.session.set({hash: request.hash});
        urlHash = request.hash;
        if (request.apiPort){
            console.log('API Port: ', request.apiPort);
            chrome.storage.session.set({apiPort: request.apiPort});
            apiPort = request.apiPort;
        }
        let home_url = request.home_url;
        captchaUrl = request.url;
        chrome.storage.session.set({captchaUrl: captchaUrl});
        // close the tab
        if (home_url){
            // open home_url and after 2 seconds close the tab
            // and open captcha_url
            chrome.tabs.create({url: home_url}, (tab) => {
                chrome.storage.session.set({home_visit: true});
                chrome.tabs.remove(sender.tab.id);
            });
        }
        else {
            chrome.tabs.create({url: captchaUrl});
            chrome.tabs.remove(sender.tab.id);
        }
    }
    return true;
});

// on message from content.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received: ', request);
    if (request.action === 'slideSlider') {
        sendToApi('blocked');
    }
    return true;
});