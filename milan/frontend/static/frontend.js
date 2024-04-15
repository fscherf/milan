'use strict';

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


// browser window -------------------------------------------------------------
class BrowserWindow {
    constructor({
        initialUrl='about:blank',
    }={}) {

        this._load_promises = new Array();
        this.cursor = window['milan']['cursor'];

        // setup HTML
        this.rootElement = renderTemplate('browser-window');

        this.iframeElement = this.rootElement.querySelector('iframe');
        this.tabTitleElement = this.rootElement.querySelector('.tab-title');
        this.backElement = this.rootElement.querySelector('.back');
        this.forwardElement = this.rootElement.querySelector('.forward');
        this.reloadElement = this.rootElement.querySelector('.reload');

        this.addressBarElement = (
            this.rootElement.querySelector('.search-bar input'));

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

        // setup address-bar
        this.addressBarElement.onfocus = () => {
            this.addressBarElement.select();
        };

        this.addressBarElement.onchange = () => {
            this._iframeNavigate({url: this.addressBarElement.value});
            this.addressBarElement.blur();
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

    _updateIframeData = () => {
        // updates the iframes title and location to the BrowserWindow object
        // tab title and address-bar

        let title = this.iframeElement.contentWindow.document.title;
        let url = this.iframeElement.contentDocument.location.href;

        if(url != this.addressBarElement.value &&
           document.activeElement != this.addressBarElement) {

            this.addressBarElement.value = url;
        }

        // when an iframes location is set to `about:blank`, its title is empty
        if(url == 'about:blank') {
            title = 'about:blank';
        }

        this.tabTitleElement.innerHTML = title;
    }

    // events -----------------------------------------------------------------
    awaitLoad = () => {
        const promise = new Promise(resolve => {
            this._load_promises.push(resolve);
        });

        return promise;
    }

    // browser functions ------------------------------------------------------
    // fullscreen
    getFullscreen = () => {
        return this.rootElement.classList.contains('fullscreen');
    }

    setFullscreen = ({
        fullscreen=true,
    }={}) => {

        if (fullscreen) {
            this.rootElement.classList.add('fullscreen');
        } else {
            this.rootElement.classList.remove('fullscreen');
        }
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

        await this.cursor.fill({
            elementOrSelector: this.addressBarElement,
            value: url,
            animation: animation,
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

    // cursor shortcuts -------------------------------------------------------
    elementExists = ({
        elementOrSelector=required('elementOrSelector'),
        timeout=undefined,
        timeoutMax=undefined,
    }={}) => {

        return this.cursor.elementExists({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            timeout: timeout,
            timeoutMax: timeoutMax,
        });
    }

    awaitElement = ({
        elementOrSelector=required('elementOrSelector'),
        timeout=undefined,
        timeoutMax=undefined,
    }={}) => {

        return this.cursor.awaitElement({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            timeout: timeout,
            timeoutMax: timeoutMax,
        });
    }

    awaitText = ({
        elementOrSelector=required('elementOrSelector'),
        timeout=undefined,
        timeoutMax=undefined,
        text=required('text'),
    }={}) => {

        return this.cursor.awaitText({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            timeout: timeout,
            timeoutMax: timeoutMax,
            text: text,
        });
    }

    click = ({
        elementOrSelector=required('elementOrSelector'),
        animation=true,
    }={}) => {

        return this.cursor.click({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            animation: animation,
        });
    }

    fill = ({
        elementOrSelector=required('value'),
        value=required('value'),
        animation=true,
    }={}) => {

        return this.cursor.fill({
            elementOrSelector: elementOrSelector,
            value: value,
            iframe: this.iframeElement,
            animation: animation,
        });
    }

    select = ({
        elementOrSelector=required('elementOrSelector'),
        value=undefined,
        index=undefined,
        label=undefined,
        animation=true,
    }={}) => {

        return this.cursor.select({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            value: value,
            index: index,
            label: label,
            animation: animation,
        });
    }

    check = ({
        elementOrSelector=required('elementOrSelector'),
        value=undefined,
        label=undefined,
        animation=true,
    }={}) => {

        return this.cursor.check({
            elementOrSelector: elementOrSelector,
            iframe: this.iframeElement,
            value: value,
            label: label,
            animation: animation,
        });
    }
}


// window manager -------------------------------------------------------------
class WindowManager {
    constructor() {
        this.windows = new Array();

        // find elements
        this.markerElement = document.querySelector('#marker');
        this.rootElement = document.querySelector('main');
        this.backgroundElement = this.rootElement.querySelector('#background');
        this.gridElement = this.rootElement.querySelector('.grid');

        // setup background
        this.backgroundElement.src = (
            `${BACKGROUND_URL}?version=${VERSION_STRING}`);

        // setup first window
        this.split();
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
}


// setup ----------------------------------------------------------------------
window.addEventListener('load', () => {
    window['milan']['windowManager'] = new WindowManager();
});
