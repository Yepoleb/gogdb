function getHash(url) {
    return url.substr(url.indexOf("#"));
}

function switchTab(url) {
    var tabLinks = document.getElementsByClassName("tabs-item");
    var tabs = document.getElementsByClassName("tab");
    var selectedTab = getHash(url);

    var tabExists = false;
    for (var i = 0; i < tabLinks.length; i++) {
        if (getHash(tabLinks[i].href) == selectedTab) {
            tabExists = true;
        }
    }

    if (!tabExists) {
        selectedTab = getHash(tabLinks[0].href)
    }
    var selectedName = selectedTab.substr(1);

    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        if (tab.id == "tab-" + selectedName) {
            tab.style.display = "";
        } else {
            tab.style.display = "none";
        }
    }

    for (var i = 0; i < tabLinks.length; i++) {
        var tabLink = tabLinks[i];
        if (getHash(tabLink.href) == selectedTab) {
            tabLink.classList.add("tabs-item-selected");
        } else {
            tabLink.classList.remove("tabs-item-selected");
        }
    }
}

function tabLinkClicked(event) {
    event.preventDefault();
    window.location.replace(event.target.href);
}

function registerEvents() {
    var tabLinks = document.getElementsByClassName("tabs-item");
    for (var i = 0; i < tabLinks.length; i++) {
        var tabLink = tabLinks[i];
        tabLink.addEventListener("click", tabLinkClicked, false);
    }
}

function initTabs() {
    registerEvents();
    switchTab(location.href);
}

function onHashChange(event) {
    switchTab(event.newURL);
}

window.addEventListener("DOMContentLoaded", initTabs, false);
window.addEventListener("hashchange", onHashChange, false);
