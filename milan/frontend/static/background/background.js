window['setWatermark'] = (text) => {
    const watermarkElement = document.querySelector('#watermark');

    watermarkElement.innerHTML = text;
};


window['setBackground'] = (background) => {
    document.body.style.background = background;
};
