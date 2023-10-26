window.addEventListener('load', (event) => {

    // setup version string
    const get_parameters = new URLSearchParams(window.location.search);
    const versionElement = document.querySelector('#version');

    versionElement.innerHTML = get_parameters.get('version');
});
