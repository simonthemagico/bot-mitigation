// content.js
if (window !== window.top) {
    // The script is in an iframe
    // Listening for messages
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        console.log('Message received in content.js:', request);
        if (request.action === "slideSlider") {
            slideSliderbg(request.xCoord);
        }
    });

    function slideSliderbg(x, retries = 0) {
        let slider = document.querySelector('.slider');
        let extraX = x / 10;

        if (slider) {
            // Starting coordinates of the slider
            let rect = slider.getBoundingClientRect();
            let startX = rect.left + (rect.width / 2);
            let startY = rect.top + (rect.height / 2);

            // Simulate mouse down
            simulateMouseEvent(slider, 'mousedown', startX, startY);

            // Simulate a more realistic mouse move
            let currentX = startX;
            let endX = startX + x + extraX; // Add extra to account for the slider width
            let steps = 20;
            let interval = 20; // Milliseconds between each step

            let moveSlider = setInterval(() => {
                // Move in small increments and check if it's close to the end
                if (Math.abs(currentX - endX) > 1) {
                    currentX += (endX - currentX) / steps;

                    // Add a slight random variation to y coordinate
                    let variationY = startY + (Math.random() - 0.5) * 10;

                    // Simulate mouse move
                    simulateMouseEvent(document, 'mousemove', currentX, variationY);
                } else {
                    // Finalize the drag, ensuring the mouseup event is near the target
                    clearInterval(moveSlider);
                    simulateMouseEvent(document, 'mouseup', endX, startY);
                    console.log(`Sliderbg moved to ${x}px`);
                }
            }, interval);

        } else {
            if (retries < 5) {
                console.log('Sliderbg not found, retrying...');
                setTimeout(() => slideSliderbg(x, retries + 1), 1000);
            } else {
                console.error('Sliderbg not found');
            }
        }
    }

    function simulateMouseEvent(element, eventName, coordX, coordY) {
        let mouseEvent = new MouseEvent(eventName, {
            view: window,
            bubbles: true,
            cancelable: true,
            clientX: coordX,
            clientY: coordY
        });

        element.dispatchEvent(mouseEvent);
    }
    console.log('content.js loaded and executed in an iframe');
} else {
    // The script is in the top-level window
    console.log('content.js loaded in the main window, not doing anything.');
}
