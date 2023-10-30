var linkTag=document.createElement('link');
linkTag.rel = "manifest"
linkTag.href = "/assets/manifest.json"
document.getElementsByTagName('head')[0].appendChild(linkTag);

// Zoom
function waitForElm(selector) {
    return new Promise(resolve => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }

        const observer = new MutationObserver(mutations => {
            if (document.querySelector(selector)) {
                observer.disconnect();
                resolve(document.querySelector(selector));
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

waitForElm('#_pages_content').then((elm) => {
    elm.addEventListener("touchstart", handlestart);
    elm.addEventListener("touchmove", handlezoom);
});

pd = 0;
function handlestart(e)
{
    if (e.touches.length == 2)
    {
        e.stopPropagation();
        pd = Math.sqrt(Math.pow(e.touches[0].clientX - e.touches[1].clientX, 2) + Math.pow(e.touches[0].clientY - e.touches[1].clientY, 2));
    }
}

function handlezoom(e)
{
    if (e.touches.length == 2)
    {
        e.stopPropagation();

        x = (e.touches[0].clientX + e.touches[1].clientX) / 2.0;
        y = (e.touches[0].clientY + e.touches[1].clientY) / 2.0;
        d = Math.sqrt(Math.pow(e.touches[0].clientX - e.touches[1].clientX, 2) + Math.pow(e.touches[0].clientY - e.touches[1].clientY, 2));
        dd = pd - d;
        pd = d;

        var newEv = new WheelEvent('wheel', {
            clientX: x,
            clientY: y, 
            deltaY: dd,
          });
        document.getElementsByClassName("nsewdrag drag")[0].dispatchEvent(newEv);
    }
}