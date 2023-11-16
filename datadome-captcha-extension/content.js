// Listening for messages
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === "slideSlider") {
        slideSliderbg(request.xCoord);
    }
});

function slideSliderbg(x) {
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
        console.error('Slider element not found');
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