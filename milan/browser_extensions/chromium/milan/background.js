'use strict';

// helper ---------------------------------------------------------------------
// header
const getHeaderIndex = (headers, name) => {
    return headers.findIndex(
        (element) => element.name.toLowerCase() === name.toLowerCase()
    );
}


const setHeader = (headers, name, value) => {
    const index = getHeaderIndex(headers, name);

    if (index == -1) {
        headers.push({
            'name': name,
            'value': value
        });
    } else {
        headers[index].value = value;
    }
}


const removeHeader = (headers, name) => {
    const index = getHeaderIndex(headers, name);

    if (index !== -1) {
        headers.splice(index, 1);
    }
}


// cookies
const parseCookie = (cookieString) => {
    const cookie = {};

    cookieString.split(';').map((cookiePart) => {
        let parts = cookiePart.split('=').map(string => string.trim());
        let key = parts[0];
        let value = parts[1] || '';

        cookie[key] = value;
    });

    return cookie;
}


const serializeCookie = (cookieObject) => {
    let cookieString = '';

    for (let [key, value] of Object.entries(cookieObject)) {
        if (value) {
            cookieString += `${key}=${value}; `;
        } else {
            cookieString += `${key}; `;
        }
    }

    return cookieString;
}


// hooks ----------------------------------------------------------------------
const onHeadersReceived = (details) => {
    const url = details.url;
    const responseHeaders = details.responseHeaders;

    // remove CORS header
    removeHeader(responseHeaders, 'X-Frame-Options');
    removeHeader(responseHeaders, 'Content-Security-Policy');

    setHeader(responseHeaders, 'Access-Control-Allow-Origin', '*');

    setHeader(
        responseHeaders,
        'Access-Control-Allow-Methods',
        'GET, PUT, POST, DELETE, HEAD, OPTIONS, PATCH',
    );

    // allow third party cookies
    const cookieHeaderIndex = getHeaderIndex(responseHeaders, 'Set-Cookie');

    if (cookieHeaderIndex != -1) {
        const cookieString = responseHeaders[cookieHeaderIndex].value;
        const cookie = parseCookie(cookieString);

        cookie['SameSite'] = 'None';
        cookie['Secure'] = '';
        cookie['Partitioned'] = '';

        delete cookie['HttpOnly'];

        setHeader(responseHeaders, 'Set-Cookie', serializeCookie(cookie));
    }

    return {
        responseHeaders: responseHeaders,
    }
}


// init -----------------------------------------------------------------------
chrome.webRequest.onHeadersReceived.addListener(
    onHeadersReceived,
    {
        urls: ['<all_urls>'],
    },
    ['blocking', 'responseHeaders', 'extraHeaders'],
);
