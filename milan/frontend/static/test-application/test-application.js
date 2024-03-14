window.addEventListener('load', () => {

    // document
    const documentTitleElement = document.querySelector('#document-title');
    const documentTitleSetElement = document.querySelector('#document-title-set');

    documentTitleSetElement.addEventListener('click', () => {
        document.title = documentTitleElement.value;
    });

    // form inputs
    const eventCountElement = document.querySelector('#event-count');
    const eventTypeElement = document.querySelector('#event-type');
    const elementIdElement = document.querySelector('#element-id');
    const elementValueElement = document.querySelector('#element-value');

    let eventCount = 0;

    // change events
    Array.from(document.querySelectorAll('.changeable')).forEach(element => {
        element.addEventListener('change', event => {
            event.preventDefault();
            event.stopPropagation();

            eventCount += 1;

            eventTypeElement.innerHTML = 'CHANGE';
            eventCountElement.innerHTML = eventCount;
            elementIdElement.innerHTML = element.id;

            if (element.type == 'checkbox') {
                elementValueElement.innerHTML = element.checked;
            } else {
                elementValueElement.innerHTML = element.value;
            }
        });
    });

    // click events
    Array.from(document.querySelectorAll('.clickable')).forEach(element => {
        element.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();

            eventCount += 1;

            eventTypeElement.innerHTML = 'CLICK';
            eventCountElement.innerHTML = eventCount;
            elementIdElement.innerHTML = element.id;
            elementValueElement.innerHTML = '-';
        });
    });

    // animations: moving button
    const movingButtonContainerElement = document.querySelector(
        '#moving-button-container',
    );

    const movingButtonElement = document.querySelector('#moving-button');

    const animateMovingButton = async () => {
        if (!animationRunning) {
            return;
        }

        let start = parseInt(movingButtonElement.style.left);
        let stop;

        if (start > 0) {
            stop = 0;
        } else {
            stop = 100;
        }

        await movingButtonElement.animate(
            {
                left: [`${start}px`, `${stop}px`],
            },
            {
                easing: 'ease',
                duration: 200,
            },
        ).finished;

        movingButtonElement.style.left = `${stop}px`;

        setTimeout(animateMovingButton, 1000);
    }

    // animations: rotating container
    const animationFramesElement = document.querySelector('#animation-frames');
    const rotatingContainerElement = document.querySelector('#rotating-container');
    const animationStartElement = document.querySelector('#animation-start');
    const animationStopElement = document.querySelector('#animation-stop');
    const animationSpeedElement = document.querySelector('#animation-speed');

    let animationRunning = false;
    let animationFrames = 0;
    let angle = 0;

	const animate = (time) => {
        angle += parseInt(animationSpeedElement.value);
        animationFrames += 1;

        if (angle >= 360) {
            angle = 0;
        }

        animationFramesElement.innerHTML = animationFrames;
        rotatingContainerElement.style['transform'] = `rotate(${angle}deg)`;

        if (animationRunning) {
            requestAnimationFrame(time => {
                animate(time);
            });
        }
    }

    // animation: controls
    animationStartElement.addEventListener('click', event => {
        animationStartElement.disabled = true;
        animationStopElement.disabled = false;
        animationRunning = true;

        animate();
        animateMovingButton();
    });

    animationStopElement.addEventListener('click', event => {
        animationStartElement.disabled = false;
        animationStopElement.disabled = true;
        animationRunning = false;
    });

    // window dimensions
    const windowWidthElement = document.querySelector('#window-width');
    const windowHeightElement = document.querySelector('#window-height');

    const updateWindowDimensions = () => {
        windowWidthElement.innerHTML = window.innerWidth;
        windowHeightElement.innerHTML = window.innerHeight;
    };

    updateWindowDimensions();

    window.addEventListener('resize', () => {
        updateWindowDimensions();
    });

    // startup time
    document.querySelector('#startup-time').innerHTML = new Date().toLocaleString();
});
