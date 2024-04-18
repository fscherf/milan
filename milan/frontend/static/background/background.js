window['setWatermark'] = (text) => {
    const watermarkElement = document.querySelector('#watermark');

    watermarkElement.innerHTML = text;
};
