function getTabName(tabLink) {
    return tabLink.href.split("#")[1];
}

function switchTab(tabName) {
    var tabs = document.getElementsByClassName("tab");
    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        if (tab.id == "tab-" + tabName) {
            tab.style.display = "";
        } else {
            tab.style.display = "none";
        }
    }

    var tabLinks = document.getElementsByClassName("tabs-item");
    for (var i = 0; i < tabLinks.length; i++) {
        var tabLink = tabLinks[i];
        if (getTabName(tabLink) == tabName) {
            tabLink.classList.add("tabs-item-selected");
        } else {
            tabLink.classList.remove("tabs-item-selected");
        }
    }
}

function onTabLinkClick(event) {
    switchTab(getTabName(event.target));
}

function initTabs() {
    var tabLinks = document.getElementsByClassName("tabs-item");

    var tabNames = [];
    for (var i = 0; i < tabLinks.length; i++) {
        var tabLink = tabLinks[i];
        tabLink.onclick = onTabLinkClick;
        tabNames.push(getTabName(tabLink));
    }

    var defaultTab = getTabName(window.location);
    if (tabNames.indexOf(defaultTab) == -1) {
        defaultTab = getTabName(tabLinks[0]);
    }

    switchTab(defaultTab);
}

window.addEventListener("DOMContentLoaded", initTabs, false);
