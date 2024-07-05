'use strict';

import { AddressBar } from './address-bar.js';

const BACKGROUND_URL = 'background/index.html';
const VERSION_STRING = 'Milan v0.0.0';
const IFRAME_UPDATE_INTERVAL = 1000;


// helper ---------------------------------------------------------------------
const required = (name) => {
    let message;

    if (typeof(name) != 'undefined') {
        message = `Argument '${name}' is required`;

    } else {
        message = 'To few arguments';
    }

    throw message;
}


const renderTemplate = (templateId) => {
    const template = document.querySelector(`template#${templateId}`)
    const node = template.content.cloneNode(true)

    return node.children[0];
}


const sleep = (ms) => {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// highlight ------------------------------------------------------------------
class Highlight {
    constructor({
        element=required('element'),
        iframe=undefined,
        borderWidth=2,
        borderStyle='solid',
        borderColor='#FF0000',
        padding=5,
        track=true,
    }={}) {

        this.element = element;
        this.iframe = iframe;
        this.borderWidth = borderWidth;
        this.borderStyle = borderStyle;
        this.borderColor = borderColor;
        this.padding = padding;
        this.track = track;

        // setup highlight element
        this.highlightElement = document.createElement('div');

        this.highlightElement.classList.add('milan-highlight');

        this.highlightElement.style.position = 'fixed';
        this.highlightElement.style.border = `${this.borderWidth}px ${this.borderStyle} ${this.borderColor}`;

        this.getDocument().body.appendChild(this.highlightElement);

        // setup tracking
        const animationFrameCallback = () => {
            this.placeHighlightElement();

            if (
                !this.track ||
                !this.element.isConnected ||
                this.getDocument() != element.ownerDocument
            ) {

                this.destroy();

                return;
            }

            requestAnimationFrame(animationFrameCallback);
        };

        requestAnimationFrame(animationFrameCallback);
    }

    getDocument = () => {
        if (typeof(this.iframe) !== undefined) {
            return this.iframe.contentDocument;
        }

        return document;
    }

    placeHighlightElement = () => {
        const clientRect = this.element.getBoundingClientRect();

        this.highlightElement.style.left = `${clientRect.left - this.padding - this.borderWidth}px`;
        this.highlightElement.style.top = `${clientRect.top - this.padding - this.borderWidth}px`;
        this.highlightElement.style.width = `${clientRect.width + (this.padding * 2)}px`;
        this.highlightElement.style.height = `${clientRect.height + (this.padding * 2)}px`;
    }

    destroy = () => {
        this.track = false;
        this.highlightElement.remove();
    }
}


// browser window -------------------------------------------------------------
class BrowserWindow {
    constructor({
        initialUrl='about:blank',
    }={}) {

        this._load_promises = new Array();
        this.highlights = new Array();
        this.cursor = window['milan']['cursor'];

        // setup HTML
        this.rootElement = renderTemplate('browser-window');

        this.iframeElement = this.rootElement.querySelector('iframe');
        this.tabTitleElement = this.rootElement.querySelector('.tab-title');
        this.tabIconImageElement = this.rootElement.querySelector('.tab-icon img');
        this.tabIconFallbackElement = this.rootElement.querySelector('.tab-icon span');
        this.tabPaneElement = this.rootElement.querySelector('.tab-pane');
        this.backElement = this.rootElement.querySelector('.back');
        this.forwardElement = this.rootElement.querySelector('.forward');
        this.reloadElement = this.rootElement.querySelector('.reload');

        // setup address bar
        this.addressBar = new AddressBar({
            browserWindow: this,
            rootElement: this.rootElement.querySelector('.address-bar'),
        });

        // setup back
        this.backElement.onclick = () => {
            this._iframeBack();
        };

        // setup forward
        this.forwardElement.onclick = () => {
            this._iframeForward();
        };

        // setup reload
        this.reloadElement.onclick = () => {
            this._iframeReload();
        };

        // setup iframe
        this.iframeElement.onload = () => {
            this._updateIframeData();

            // resolve all pending promises in _load_promises
            let resolve;

            while (this._load_promises.length > 0) {
                resolve = this._load_promises.pop();

                resolve();
            }
        };

        // It seems to be impossible to get notified on iframe location changes
        // reliably. Therefore, we poll it periodically.
        setInterval(() => {
            this._updateIframeData();
        }, IFRAME_UPDATE_INTERVAL);

        this._iframeNavigate({url: initialUrl});
    }

    _iframeNavigate = ({
        url=required('url'),
    }={}) => {
        // Sets the URL shown in the iframe, and cares about missing
        // protocol and port if necessary.
        // FIXME: add support for missing host

        // prefix URL if necessary to prevent cross origin problems
        if(!url.startsWith('about:') &&
               !url.startsWith('http://') &&
               !url.startsWith('https://')) {

            url = `http://${url}`;
        }

        this.iframeElement.src = url;
    }

    _iframeBack = () => {
        this.iframeElement.contentWindow.history.back();
    }

    _iframeForward = () => {
        this.iframeElement.contentWindow.history.forward();
    }

    _iframeReload = () => {
        this.iframeElement.contentDocument.location.reload();
    }

    _getIframeFaviconURL = async () => {
        const _document = this.iframeElement.contentDocument;
        const linkElements = _document.getElementsByTagName('link');
        const urls = [];

        let url = '';

        // find URLs
        for (const linkElement of linkElements) {
            if ((linkElement.getAttribute('rel') === 'icon') ||
                (linkElement.getAttribute('rel') === 'shortcut icon') ||
                (linkElement.getAttribute('rel') === 'apple-touch-icon')) {

                urls.push(linkElement.getAttribute('href'));
            }
        }

        // find best quality URL
        const findUrl = (extension) => {
            for(const url of urls) {
                if (url.endsWith(extension)) {
                    return url;
                }
            }
        }

        url = findUrl('.ico');

        if (!url) {
            url = findUrl('.svg');
        }

        url = urls.at(-1);

        // URL fallback
        if (!url) {
            url = '/favicon.ico';
        }

        // resolve URL
        if (url) {
            // URLs can be
            //   - https://example.org/favicon.ico
            //   - /favicon.ico
            //   - ./favicon.ico
            
            try {
                url = (new URL(url, new URL(this.getUrl()))).toString();
            } catch {
                url = '';
            }
        }

        // check if url is actually loadable
        if (url) {
            const response = await fetch(
                url,
            ).then(response => {
                if (!response.ok) {
                    url = '';
                }
            }).catch(error => {
                url = '';
            });
        }

        return url;
    }

    _updateIframeData = async () => {
        // updates the iframes title and location to the BrowserWindow object
        // tab title and address-bar

        const url = this.iframeElement.contentDocument.location.href;

        let title = this.iframeElement.contentWindow.document.title;

        if(url != this.addressBar.getValue()) {
            this.addressBar.setValue(url);
        }

        // when an iframes location is set to `about:blank`, its title is empty
        if(url.startsWith('about:blank')) {
            title = 'about:blank';
        }

        this.tabTitleElement.innerHTML = title;

        // favicon
        const faviconURL = await this._getIframeFaviconURL();

        if (faviconURL) {
            this.tabIconImageElement.src = faviconURL;
            this.tabIconImageElement.style.display = 'block';
            this.tabIconFallbackElement.style.display = 'none';
        } else {
            this.tabIconImageElement.style.display = 'none';
            this.tabIconFallbackElement.style.display = 'block';
        }
    }

    getSize = () => {
        return {
            width: this.iframeElement.clientWidth,
            height: this.iframeElement.clientHeight,
        };
    }

    // events -----------------------------------------------------------------
    awaitLoad = () => {
        const promise = new Promise(resolve => {
            this._load_promises.push(resolve);
        });

        return promise;
    }

    // browser functions ------------------------------------------------------
    addStyleSheet = ({
        text=required('text'),
    }={}) => {
        return window.milan.addStyleSheet({
            text: text,
            iframe: this.iframeElement,
        });
    }

    // fullscreen
    getFullscreen = () => {
        return (
            this.rootElement.classList.contains('fullscreen') ||
            this.tabPaneElement.classList.contains('fullscreen')
        )
    }

    setFullscreen = async ({
        fullscreen=true,
        decorations=true,
    }={}) => {


        // reset full screen
        this.rootElement.classList.remove('fullscreen');
        this.tabPaneElement.classList.remove('fullscreen');

        // set fullscreen
        if (fullscreen) {
            if (decorations) {
                this.rootElement.classList.add('fullscreen');
            } else {
                this.tabPaneElement.classList.add('fullscreen');
            }
        }

        // give the browser time to rerender
        await sleep(0);
    }

    // navigation
    navigate = async ({
        url=required('url'),
        animation=true,
    }={}) => {

        const loadPromise = this.awaitLoad();

        // in fullscreen, the address bar is not visible
        // therefore we skip all animations
        if (this.getFullscreen()) {
            this._iframeNavigate({url: url});

            await loadPromise;

            return;
        }

        await this.cursor.click({
            elementOrSelector: this.addressBar.rootElement,
            animation: animation,
        });

        await this.cursor.fill({
            elementOrSelector: this.addressBar.inputElement,
            value: url,
            animation: false,
        });

        await loadPromise;

        if (animation) {
            await sleep(300);
        }
    }

    reload = async ({
        animation=true,
    }) => {

        const loadPromise = this.awaitLoad();

        // in fullscreen, the reload button is not visible
        // therefore we skip all animations
        if (this.getFullscreen()) {
            this._iframeReload();

            await loadPromise;

            return;
        }

        await this.cursor.click({
            elementOrSelector: this.reloadElement,
            animation: animation,
        });

        await loadPromise;

        if (animation) {
            await sleep(200);
        }
    }

    navigateBack = async ({
        animation=true,
    }) => {

        const loadPromise = this.awaitLoad();

        // in fullscreen, the back button is not visible
        // therefore we skip all animations
        if (this.getFullscreen()) {
            this._iframeBack();

            await loadPromise;

            return;
        }

        await this.cursor.click({
            elementOrSelector: this.backElement,
            animation: animation,
        });

        await loadPromise;

        if (animation) {
            await sleep(200);
        }
    }

    navigateForward = async ({
        animation=true,
    }) => {

        const loadPromise = this.awaitLoad();

        // in fullscreen, the forward button is not visible
        // therefore we skip all animations
        if (this.getFullscreen()) {
            this._iframeForward();

            await loadPromise;

            return;
        }

        await this.cursor.click({
            elementOrSelector: this.forwardElement,
            animation: animation,
        });

        await loadPromise;

        if (animation) {
            await sleep(200);
        }
    }

    getUrl = () => {
        return this.iframeElement.contentDocument.location.href;
    }

    evaluate = async ({
        expression=required('expression'),
    }={}) => {

        let returnValue = this.iframeElement.contentWindow.eval(expression);

        if (returnValue instanceof Promise) {
            returnValue = await returnValue;
        }

        return returnValue;
    }

    // highlights -------------------------------------------------------------
    highlightElements = async ({
        selectors=required('selectors'),
        text=undefined,
        index=undefined,
        count=undefined,
        retryInterval=undefined,
        timeout=undefined,
        borderWidth=undefined,
        borderStyle=undefined,
        borderColor=undefined,
        padding=undefined,
        track=undefined,
        duration=undefined,
    }={}) => {

        const elements = await this.awaitElements({
            selectors: selectors,
            text: text,
            count: count,
            index: index,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });

        const highlights = [];

        let highlight;

        // scroll element into view if needed
        // FIXME: move cursor onto iframe if needed
        const firstElementIsVisible = this.cursor.elementIsVisible({
            element: elements[0],
            iframe: this.iframeElement,
        });

        if (!firstElementIsVisible) {
            elements[0].scrollIntoView({
                behavior: 'smooth',
                inline: 'nearest',

                // the element has to be centered because the highlight
                // element has some padding around the element
                block: 'center',
            });

            await sleep(750);
        }

        // highlight elements
        for (const element of elements) {
            highlight = new Highlight({
                iframe: this.iframeElement,
                element: element,
                borderWidth: borderWidth,
                borderStyle: borderStyle,
                borderColor: borderColor,
                padding: padding,
                track: track,
            });

            if(duration) {
                highlights.push(highlight);
            } else {
                this.highlights.push(highlight);
            }
        }

        if (duration) {
            await sleep(duration);

            for(const highlight of highlights) {
                highlight.destroy();
            }
        }

        // return count of elements that are/were highlighted
        return elements.length;
    }

    removeHighlights = async () => {
        for(const highlight of this.highlights) {
            highlight.destroy();
        }
    }

    // cursor shortcuts -------------------------------------------------------
    getElementCount = ({
        selector=required('selector'),
    }={}) => {

        return this.cursor.getElementCount({
            selector:  selector,
            iframe: this.iframeElement,
        });
    }

    elementExists = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.elementExists({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    awaitElement = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        returnElement=true,
        retryInterval=retryInterval,
        timeout=undefined,
    }={}) => {

        return this.cursor.awaitElement({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            returnElement: returnElement,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    awaitElements = ({
        selectors=required('selectors'),
        text='',
        present=true,
        matchAll=true,
        count=undefined,
        index=undefined,
        returnElements=true,
        iframe=undefined,
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.awaitElements({
            selectors: selectors,
            text: text,
            present: present,
            matchAll: matchAll,
            count: count,
            index: index,
            returnElements: returnElements,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    awaitText = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        retryInterval=undefined,
        timeout=undefined,
        text=required('text'),
    }={}) => {

        return this.cursor.awaitText({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
            text: text,
        });
    }

    click = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        animation=true,
    }={}) => {

        return this.cursor.click({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            animation: animation,
        });
    }

    fill = ({
        elementOrSelector=required('value'),
        elementIndex=0,
        value=required('value'),
        animation=true,
    }={}) => {

        return this.cursor.fill({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            value: value,
            iframe: this.iframeElement,
            animation: animation,
        });
    }

    select = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        value=undefined,
        index=undefined,
        label=undefined,
        animation=true,
    }={}) => {

        return this.cursor.select({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            value: value,
            index: index,
            label: label,
            animation: animation,
        });
    }

    check = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        value=undefined,
        label=undefined,
        animation=true,
    }={}) => {

        return this.cursor.check({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            value: value,
            label: label,
            animation: animation,
        });
    }

    getText = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        retryInterval: retryInterval,
        timeout=undefined,
    }={}) => {

        return this.cursor.getText({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    getHtml = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.getHtml({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    setHtml = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        html=required('html'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.setHtml({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            html: html,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    getAttribute = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        name=required('name'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.getAttribute({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            name: name,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    getAttributes = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.getAttributes({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    setAttributes = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        attributes=required('attributes'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.setAttributes({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            attributes: attributes,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    removeAttributes = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        names=required('names'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.removeAttributes({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            names: names,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    classListAdd = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        names=required('names'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.classListAdd({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            names: names,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }

    classListRemove = ({
        elementOrSelector=required('elementOrSelector'),
        elementIndex=0,
        names=required('names'),
        retryInterval=undefined,
        timeout=undefined,
    }={}) => {

        return this.cursor.classListRemove({
            elementOrSelector: elementOrSelector,
            elementIndex: elementIndex,
            names: names,
            iframe: this.iframeElement,
            retryInterval: retryInterval,
            timeout: timeout,
        });
    }
}


// window manager -------------------------------------------------------------
class WindowManager {
    constructor() {
        this.windows = new Array();

        this._background_load_promises = new Array();

        // find elements
        this.markerElement = document.querySelector('#marker');
        this.rootElement = document.querySelector('main');
        this.pixelElement = document.querySelector('#pixel');
        this.backgroundElement = this.rootElement.querySelector('#background');
        this.gridElement = this.rootElement.querySelector('.grid');

        // setup background iframe
        this.backgroundElement.onload = () => {
            let resolve;

            while (this._background_load_promises.length > 0) {
                resolve = this._background_load_promises.pop();

                resolve();
            }
        };

        // setup first window
        this.split();
    }

    _getBackgroundLoadPromise = () => {
        return new Promise(resolve => {
            this._background_load_promises.push(resolve);
        });
    }

    getSize = () => {
        return {
            width: this.rootElement.clientWidth,
            height: this.rootElement.clientHeight,
        };
    }

    split = () => {
        if(this.windows.length > 3) {
            throw('More than 4 windows are not supported');
        }

        const browserWindow = new BrowserWindow({
            initialUrl: 'about:blank',
        });

        const rowElement = renderTemplate('row');
        const columnElements = this.gridElement.querySelectorAll('.column');

        rowElement.appendChild(browserWindow.rootElement);

        if(this.windows.length < 2) {
            const columnElement = renderTemplate('column');

            columnElement.appendChild(rowElement);
            this.gridElement.appendChild(columnElement);

        } else if(this.windows.length == 2) {
            columnElements[1].appendChild(rowElement);

        } else if(this.windows.length == 3) {
            columnElements[0].appendChild(rowElement);
        }

        this.windows.push(browserWindow);
    }

    getWindow = ({
        index=0,
    }={}) => {
        return this.windows[index];
    }

    getWindowCount = () => {
        return this.windows.length;
    }

    setBackgroundUrl = async ({
        url=required('url'),
    }={}) => {

        const promise = this._getBackgroundLoadPromise();

        this.backgroundElement.src = url;

        await promise;
    }

    setWatermark = ({
        text=required('text'),
    }={}) => {
        this.backgroundElement.contentWindow.setWatermark(text);
    }

    setBackground = ({
        background=required('background'),
    }={}) => {
        this.backgroundElement.contentWindow.setBackground(background);
    }

    forceRerender = async () => {
        const clone = this.pixelElement.cloneNode();

        this.pixelElement.replaceWith(clone);
        this.pixelElement = clone;

        await sleep(0);
    }
}


// setup ----------------------------------------------------------------------
window.addEventListener('load', () => {
    window['milan']['windowManager'] = new WindowManager();
});
