(() => {
    'use strict';

    // source: https://cursor.in/
    const CURSOR_SVG_SOURCE = `<?xml version="1.0" encoding="utf-8"?>
<!-- Generator: Adobe Illustrator 18.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 28 28" enable-background="new 0 0 28 28" xml:space="preserve">
<polygon fill="#FFFFFF" points="8.2,20.9 8.2,4.9 19.8,16.5 13,16.5 12.6,16.6 "/>
<polygon fill="#FFFFFF" points="17.3,21.6 13.7,23.1 9,12 12.7,10.5 "/>
<rect x="12.5" y="13.6" transform="matrix(0.9221 -0.3871 0.3871 0.9221 -5.7605 6.5909)" width="2" height="8"/>
<polygon points="9.2,7.3 9.2,18.5 12.2,15.6 12.6,15.5 17.4,15.5 "/>
</svg>`;

    const CURSOR_WIDTH = 28;
    const CURSOR_HEIGHT = 28;
    const CURSOR_OFFSET_LEFT = -4;
    const CURSOR_OFFSET_TOP = -4;

    const required = (name) => {
        let message;

        if (typeof(name) != 'undefined') {
            message = `Argument '${name}' is required`;

        } else {
            message = 'To few arguments';
        }

        throw message;
    }


    const sleep = (ms) => {
        return new Promise(resolve => setTimeout(resolve, ms));
    }


    const run = async ({
        func=required('func'),
        args=required('args'),
    }={}) => {

        let exitCode = 0;
        let returnValue = undefined;
        let errorMessage = '';
        let errorStack = '';

        try {
            returnValue = func(args);

            if (returnValue instanceof Promise) {
                returnValue = await returnValue;
            }

        } catch (error) {
            exitCode = 1;
            returnValue = undefined;
            errorMessage = error.toString();

            if (error.stack) {
                errorStack = error.stack.toString();
            }
        }

        // keep JSON.stringify from removing returnValue when func
        // returned undefined
        if (returnValue === undefined) {
            returnValue = null;
        }

        return {
            exitCode: exitCode,
            returnValue: returnValue,
            errorMessage: errorMessage,
            errorStack: errorStack,
        };
    }


    class Cursor {
        constructor() {

            // setup config
            this.config = {
                shortTimeout: 200,
                shortTimeoutMax: 1000,
                timeout: 200,
                timeoutMax: 3000,
                maxRetries: 3,
            };

            // setup cursor element
            this.cursorElement = this.svgStringToElement({
                svgString: CURSOR_SVG_SOURCE,
            });

            this.cursorElement.style.position = 'fixed';
            this.cursorElement.style.zIndex = '1000000';
            this.cursorElement.style.width = `${CURSOR_WIDTH}px`;
            this.cursorElement.style.height = `${CURSOR_HEIGHT}px`;

            this.show();

            // initial position
            this.cursorX = 0;
            this.cursorY = 0;

            this.moveToHome({animation: false});

            // append cursor to the DOM
            document.body.appendChild(this.cursorElement);
        }

        // misc helper --------------------------------------------------------
        svgStringToElement = ({
            svgString=required('svgString'),
        }={}) => {
            return new DOMParser()
                .parseFromString(svgString, 'image/svg+xml')
                .documentElement;
        }

        // cursor element helper ----------------------------------------------
        hide = () => {
            this.cursorElement.style.display = 'none';
        }

        show = () => {
            this.cursorElement.style.display = 'block';
        }

        isVisible = () => {
            return this.cursorElement.style.display == 'block';
        }

        getPosition = () => {
            return {
                x: this.cursorX,
                y: this.cursorY,
            };
        }

        // element helper -----------------------------------------------------
        getElementCount = ({
            selector=required('selector'),
            iframe=undefined,
        }={}) => {

            let _document = document;

            if (typeof(iframe) != 'undefined') {
                _document = iframe.contentDocument;
            }

            return _document.querySelectorAll(selector).length;
        }

        getElement = ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
        }={}) => {

            let _document = document;
            let element = elementOrSelector;

            if (typeof(iframe) != 'undefined') {
                _document = iframe.contentDocument;
            }

            if (typeof(element) == 'string') {
                element = _document.querySelectorAll(
                    elementOrSelector,
                )[elementIndex];
            }

            return element;
        }

        elementExists = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            let element = undefined;
            let timeSlept = 0;

            timeout = timeout || this.config.shortTimeout;
            timeoutMax = timeoutMax || this.config.shortTimeoutMax;

            while (timeSlept < timeoutMax) {
                element = this.getElement({
                    elementOrSelector: elementOrSelector,
                    elementIndex: elementIndex,
                    iframe: iframe,
                    timeout: timeout,
                    timeoutMax: timeoutMax,
                });

                if (element) {
                    return true;
                }

                await sleep(timeout);

                timeSlept += timeout;
            }

            return false;
        }

        awaitElement = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            returnElement=true,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            let element = undefined;
            let timeSlept = 0;

            timeout = timeout || this.config.timeout;
            timeoutMax = timeoutMax || this.config.timeoutMax;

            while (timeSlept < timeoutMax) {
                element = this.getElement({
                    elementOrSelector: elementOrSelector,
                    elementIndex: elementIndex,
                    iframe: iframe,
                    timeout: timeout,
                    timeoutMax: timeoutMax,
                });

                if (element) {
                    if (returnElement) {
                        return element;
                    }

                    return;
                }

                await sleep(timeout);

                timeSlept += timeout;
            }

            throw `No element with selector '${elementOrSelector}' found`;
        }

        awaitText = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
            text=required('text'),
        }={}) => {

            timeout = timeout || this.config.timeout;
            timeoutMax = timeoutMax || this.config.timeoutMax;

            let element = undefined;
            let timeSlept = 0;

            while (timeSlept < timeoutMax) {
                element = this.getElement({
                    elementOrSelector: elementOrSelector,
                    elementIndex: elementIndex,
                    iframe: iframe,
                    timeout: timeout,
                    timeoutMax: timeoutMax,
                });

                if (element && element.innerHTML.includes(text)) {
                    return;
                }

                await sleep(timeout);

                timeSlept += timeout;
            }

            throw `No element with selector '${elementOrSelector}' and text '${text}' found`;
        }

        elementIsVisible = ({
            element=required('element'),
            iframe=undefined,
        }={}) => {

            const clientRect = element.getBoundingClientRect();
            let width = window.innerWidth;
            let height = window.innerHeight;

            if (typeof(iframe) != 'undefined') {
                const iframeClientRect = iframe.getBoundingClientRect();

                width = iframeClientRect.wdith;
                height = iframeClientRect.height;
            }

            return (
                clientRect.top >= 0 &&
                clientRect.left >= 0 &&
                clientRect.bottom <= (
                    height ||
                    document.documentElement.clientHeight) &&
                clientRect.right <= (
                    width ||
                    document.documentElement.clientWidth)
            );
        }

        getElementCoordinates = ({
            element=required('element'),
            iframe=undefined,
        }={}) => {

            const clientRect = element.getBoundingClientRect();

            let x = clientRect.x + (clientRect.width / 2);
            let y = clientRect.y + (clientRect.height / 2);

            if (typeof(iframe) != 'undefined') {
                const iframeClientRect = iframe.getBoundingClientRect();

                x += iframeClientRect.x;
                y += iframeClientRect.y;
            }

            return {
                x: x,
                y: y,
            }
        }

        getText = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            return element.textContent;
        }

        getHtml = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            return element.innerHTML;
        }

        setHtml = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            html=required('html'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            element.innerHTML = html;
        }

        getAttribute = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            name=required('name'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            return element.getAttribute(name);
        }

        getAttributes = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            let attributes = {};

            for (let index = 0; index < element.attributes.length; index++) {
                let attribute = element.attributes[index];

                attributes[attribute.nodeName] = attribute.nodeValue;
            }

            return attributes;
        }

        setAttributes = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            attributes=required('attributes'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            for (let [name, value] of Object.entries(attributes)) {
                element.setAttribute(name, value);
            }
        }

        removeAttributes = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            names=required('names'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            for (let name of Array.from(names)) {
                element.removeAttribute(name);
            }
        }

        classListAdd = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            names=required('names'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            for (let name of Array.from(names)) {
                element.classList.add(name);
            }
        }

        classListRemove = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            names=required('names'),
            iframe=undefined,
            timeout=undefined,
            timeoutMax=undefined,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
                timeout: timeout,
                timeoutMax: timeoutMax,
            });

            for (let name of Array.from(names)) {
                element.classList.remove(name);
            }
        }

        // animations ---------------------------------------------------------
        _playClickAnimation = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            maxRetries=undefined,
            iframe=undefined,
        }={}) => {

            // FIXME: add custom offsets

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            // scroll element into view if needed
            // FIXME: move cursor onto iframe if needed
            if (!this.elementIsVisible({element: element, iframe: iframe})) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'end',
                    inline: 'nearest',
                });

                await sleep(500);
            }

            // place cursor
            const max_retries = maxRetries || this.config.maxRetries;

            let coordinates_before_cursor_move;
            let coordinates_after_cursor_move;
            let tries = 0;

            while (tries < max_retries) {
                coordinates_before_cursor_move = this.getElementCoordinates({
                    element: element,
                    iframe: iframe,
                });

                await this.moveTo({
                    x: coordinates_before_cursor_move.x,
                    y: coordinates_before_cursor_move.y,
                    animation: true,
                });

                await sleep(250);

                coordinates_after_cursor_move = this.getElementCoordinates({
                    element: element,
                    iframe: iframe,
                });

                // element moved; retrying
                if (Object.entries(coordinates_before_cursor_move).toString() !==
                    Object.entries(coordinates_after_cursor_move).toString()) {

                    tries += 1;

                    continue;
                }

                // click animation
                await this.cursorElement.animate(
                    {
                        width: [`${CURSOR_WIDTH}px`, `${CURSOR_WIDTH-8}px`],
                        height: [`${CURSOR_HEIGHT}px`, `${CURSOR_HEIGHT-8}px`],
                    },
                    {
                        easing: 'ease',
                        duration: 200,
                    },
                ).finished;

                // finish
                return;
            }

            throw `Element with selector moved to much under the cursor`;
        }

        // actions ------------------------------------------------------------
        moveTo = async ({
            x=required('x'),
            y=required('y'),
            animation=true,
        }={}) => {

            // FIXME: when animations are switched off position queries come
            // back incorrect after movement

            const absoluteX = x + CURSOR_OFFSET_LEFT;
            const absoluteY = y + CURSOR_OFFSET_TOP;

            if(!animation) {
                this.cursorX = x;
                this.cursorY = y;
                this.cursorElement.style.left = `${absoluteX}px`;
                this.cursorElement.style.top = `${absoluteY}px`;

                return;
            }

            await this.cursorElement.animate(
                {
                    left: [`${this.cursorX}px`, `${absoluteX}px`],
                    top: [`${this.cursorY}px`, `${absoluteY}px`],
                },
                {
                    easing: 'ease',
                    duration: 300,
                    fill: 'forwards',
                },
            ).finished;

            this.cursorX = x;
            this.cursorY = y;
        }

        click = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            animation=true,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            if (animation) {
                await this._playClickAnimation({
                    elementOrSelector: element,
                    iframe: iframe,
                });
            }

            element.click();

            if (animation) {
                await sleep(500);
            }
        }

        focus = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            animation=true,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            if (animation) {
                await this._playClickAnimation({
                    elementOrSelector: element,
                    iframe: iframe,
                });
            }

            element.focus();

            if (animation) {
                await sleep(300);
            }
        }

        fill = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            value=required('value'),
            animation=true,
        }) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            const lastValue = element.value;

            if (animation) {
                await this.focus({
                    elementOrSelector: element,
                    iframe: iframe,
                    animation: animation,
                });
            }

            // set value
            element.value = value;

            if (animation) {
                await sleep(200);
            }

            // fire input change
            const inputEvent = new Event(
                'input',
                {
                    target: element,
                    bubbles: true,
                },
            );

            // React: https://github.com/facebook/react/issues/11488
            // React 15
            inputEvent.simulated = true;

            // React 16
            if (element._valueTracker) {
                element._valueTracker.setValue(lastValue);
            }

            element.dispatchEvent(inputEvent);

            // fire change event
            const changeEvent = new Event(
                'change',
                {
                    target: element,
                    bubbles: true,
                },
            );

            element.dispatchEvent(changeEvent);
        }

        check = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            value=true,
            animation=true,
        }={}) => {

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            if (element.checked == value) {
                // nothing to do

                return;
            }

            await this.click({
                elementOrSelector: element,
                elementIndex: elementIndex,
                iframe: iframe,
                animation: animation,
            });
        }

        select = async ({
            elementOrSelector=required('elementOrSelector'),
            elementIndex=0,
            iframe=undefined,
            value=undefined,
            index=undefined,
            label=undefined,
            animation=true,
        }={}) => {

            if (index == undefined &&
                    value == undefined &&
                    label == undefined) {

                throw 'To few arguments';
            }

            const element = await this.awaitElement({
                elementOrSelector: elementOrSelector,
                elementIndex: elementIndex,
                iframe: iframe,
            });

            // focus element
            await this.focus({
                elementOrSelector: element,
                elementIndex: elementIndex,
                iframe: iframe,
                animation: animation,
            });

            // actual select option
            if (value != undefined) {
                element.value = value;

            } else if (index != undefined) {
                element.selectedIndex = index;

            } else if (label != undefined) {
                const options = Array.from(element.querySelectorAll('option'));

                options.forEach((option, index) => {
                    if (option.innerHTML != label) {
                        return;
                    }

                    element.selectedIndex = index;
                });
            }

            if (animation) {
                await sleep(200);
            }

            // issue change event
            element.dispatchEvent(new Event('change'));
        }

        moveToHome = async ({
            animation=true,
        }={}) => {

            await this.moveTo({
                x: window.innerWidth / 2,
                y: window.innerHeight / 2,
                animation: animation,
            });
        }
    }


    // setup ------------------------------------------------------------------
    window.addEventListener('load', () => {
        window['milan'] = {
            run: run,
            cursor: new Cursor(),
        };
    });
})();
