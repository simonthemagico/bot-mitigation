let refererUrl = ''; // Global variable to store referer

// SHA-256 hash function
async function sha256_hash(s) {
    const msgBuffer = new TextEncoder().encode(s); // encode as UTF-8
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer); // hash the message
    const hashArray = Array.from(new Uint8Array(hashBuffer)); // convert buffer to byte array
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join(''); // convert bytes to hex string
    return hashHex;
}

chrome.webRequest.onCompleted.addListener(
    function (details) {
        if (details.initiator && details.initiator.includes('chrome-extension://')) {
            console.log('Skipping download triggered by the extension itself');
            return;
        }

        console.log('Request completed: ', details.url);

        if (details.url.includes('https://geo.captcha-delivery.com/captcha/check')) {
            processResponse(details);
        }
        
        if (details.url.includes('https://geo.captcha-delivery.com/captcha/?initialCid')) {
            capturePreloadImages(details);
        }
    },
    { urls: ["<all_urls>"] },
    ["responseHeaders"]
);

function processResponse(details) {
    // Modify URL to include parent_url
    let modifiedUrl = new URL(details.url);
    console.log(`Search params: ${modifiedUrl.searchParams}`)
    modifiedUrl.searchParams.set('parent_url', refererUrl);

    console.log('Modified URL:', modifiedUrl);
    
    fetch(modifiedUrl)
        .then(response => handleResponse(response, details.tabId, modifiedUrl))
        .catch(handleError);
}

async function sendBackToApi(backResponse, url) {
    const hashedUrl = await sha256_hash(url);
    // send post request to http://localhost:8000/v1/response
    const requestUrl = `http://localhost:8000/v1/response`;

    backResponse['hashedUrl'] = hashedUrl;

    fetch(requestUrl, {
        method: 'POST',
        body: JSON.stringify(backResponse),
        headers: { 'Content-Type': 'application/json' }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            console.log('Response sent to API');
        })
        .catch(error => {
            console.error('Error sending response to API: ', error);
        });
}

// New function to capture preload images
async function capturePreloadImages(details) {
    chrome.scripting.executeScript({
        target: { tabId: details.tabId },
        function: () => Array.from(document.querySelectorAll('link[rel="preload"]')).map(link => link.href)
    }, async (results) => { // Added async here
        console.log(results);
        if (chrome.runtime.lastError || !results || results.length === 0) {
            console.error('Error in fetching preload image URLs: ', chrome.runtime.lastError);

            // Write error to responses file that it is blocked
            const backResponse = {
                "url": details.url,
                "body": "Preload images blocked"
            }
            await sendBackToApi(backResponse, details.url);
            
            return;
        }

        let imageUrls = results[0].result;
        console.log('Preload image URLs:', imageUrls);

        // Process the URLs as needed
        // Image containing .frag. is piece image
        // Image not containing .frag. is background image
        let bgImageUrl = imageUrls.find(url => !url.includes('.frag.'));
        let pieceImageUrl = imageUrls.find(url => url.includes('.frag.'));

        if (bgImageUrl && pieceImageUrl) {
            solvePuzzle(bgImageUrl, pieceImageUrl, details.tabId);
        } else {
            console.error('Background image or piece image not found');
            // Blocked
            const backResponse = {
                "url": details.url,
                "body": "Ip blocked"
            }
            await sendBackToApi(backResponse, details.url);
        }
    });

    // Extract referer from URL
    const urlParams = new URLSearchParams(new URL(details.url).search);
    refererUrl = urlParams.get('referer');

    console.log('Referer URL:', refererUrl);
}

function solvePuzzle(bgImageUrl, pieceImageUrl, tabId) {
    const url = `https://captcha.riseofninja.com/api/v1/puzzleSolver`;
    fetch(url, {
        method: 'POST',
        body: JSON.stringify({ bgImageUrl: bgImageUrl, pieceImageUrl: pieceImageUrl }),
        headers: { 'Content-Type': 'application/json' }
    })
        .then(response => response.json())
        .then(data => {
            const xCoordinate = data.x;
            // Code to slide 'sliderbg' by xCoordinate
            console.log(`Slide 'sliderbg' by x position: ${xCoordinate}`);

            // Simulate the slider movement using chrome.scripting.executeScript
            // slideSliderbg(xCoordinate);
            chrome.tabs.sendMessage(tabId, {action: "slideSlider", xCoord: xCoordinate});
        })
        .catch(error => {
            console.error('Error in puzzle solving: ', error);
        });
}

function handleResponse(response, tabId, modifiedUrl) {
    if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
    }
    chrome.tabs.get(tabId, function(tab) {
        if (chrome.runtime.lastError) {
            console.error('Error getting tab: ', chrome.runtime.lastError);
            return;
        }
        const tabUrl = tab.url;
        console.log('Tab URL:', tabUrl);
        response.text().then(text => initiateDownload(text, tabUrl, modifiedUrl));
    });
}

// Modified initiateDownload function to use sha256_hash
async function initiateDownload(text, tabUrl, modifiedUrl) {
    console.log('Response text:', text);
    const backResponse = {
        "url": modifiedUrl,
        "body": JSON.parse(text)
    }
    await sendBackToApi(backResponse, tabUrl);
}

function handleError(error) {
    console.error('Error fetching the response: ', error);
}

chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed and background service worker started.');
});