// ==UserScript==
// @name GOG DB Integration
// @description Add a GOG DB button to the GOG store
// @version 0.1
// @author Yepoleb
// @license CC0
// @namespace https://gogdb.org
// @icon https://gogdb.org/static/img/gogdb_48x48.png
// @run-at document-end
// @match https://www.gog.com/game/*
// @grant none
// ==/UserScript==


var button_element = document.createElement("a");
button_element.innerHTML = '<img src="https://www.gogdb.org/static/img/gogdb_trans_15x15.png" alt="" style="height: 15px; margin-right: 0.5em">GOG Database';
button_element.setAttribute("href", "https://www.gogdb.org/product/" + gogData.gameProductData.id);
button_element.className = "wishlist-btn";
button_element.setAttribute("style", "display: flex; flex-direction: row; justify-content: center; align-items: center");
button_element.setAttribute("target", "_blank");

var socials_element = document.getElementsByClassName("socials")[0];
socials_element.parentNode.insertBefore(button_element, socials_element.nextSibling);

