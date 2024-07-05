'use strict';

export class AddressBar {
    constructor({
        browserWindow,
        rootElement,
    }) {

        this.browserWindow = browserWindow;
        this.rootElement = rootElement;
        this.focused = false;
        this.value = '';

        // find elements
        this.inputElement = this.rootElement.querySelector('input');
        this.iconElement = this.rootElement.querySelector('.material-icon');
        this.protocolElement = this.rootElement.querySelector('.protocol');
        this.separatorElement = this.rootElement.querySelector('.separator');
        this.textElement = this.rootElement.querySelector('.text');

        // setup event handler
        this.rootElement.addEventListener('click', () => {
            this.focus();
        });

        this.inputElement.addEventListener('blur', () => {
            this.blur();
        });

        this.inputElement.addEventListener('change', () => {
            this.value = this.inputElement.value.trim();

            this.browserWindow._iframeNavigate({
                url: this.value,
            });

            this.blur();
        });
    }

    getValue = () => {
        return this.value;
    }

    setValue = (value) => {
        if (this.focused) {
            return;
        }

        this.inputElement.value = value;
        this.value = value;
        this.update()
    }

    update = () => {

        // valid URL
        try {
            const url = new URL(this.getValue());

            if (url.protocol == 'https:') {
                this.rootElement.classList.add('secure');
                this.iconElement.innerHTML = 'lock';
            } else {
                this.rootElement.classList.remove('secure');
                this.iconElement.innerHTML = 'error';
            }

            if (url.protocol == 'about:') {
                this.protocolElement.innerHTML = '';
                this.separatorElement.innerHTML = '';
                this.textElement.innerHTML = 'about:blank';
            } else {
                this.protocolElement.innerHTML = url.protocol.slice(0, -1);
                this.separatorElement.innerHTML = '://';
                this.textElement.innerHTML = url.toString().split('://')[1];
            }

        // invalid URL
        } catch {
            this.rootElement.classList.remove('secure');
            this.iconElement.innerHTML = 'error';
            this.protocolElement.innerHTML = '';
            this.separatorElement.innerHTML = '';
            this.textElement.innerHTML = this.getValue();
        }
    }

    focus = () => {
        this.focused = true;
        this.rootElement.classList.add('focus');
        this.inputElement.focus();
        this.inputElement.select();
    }

    blur = () => {
        this.focused = false;
        this.rootElement.classList.remove('focus');
        this.inputElement.blur();
    }
}
