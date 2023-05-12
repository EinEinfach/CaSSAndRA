var linkTag=document.createElement('link');
linkTag.rel = "manifest"
linkTag.href = "/assets/manifest.json"
document.getElementsByTagName('head')[0].appendChild(linkTag);