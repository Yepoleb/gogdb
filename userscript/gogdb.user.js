// ==UserScript==
// @name GOG DB Integration
// @description Add a GOG DB button to the GOG store
// @version 0.3
// @author Yepoleb
// @license CC0
// @namespace https://gogdb.org
// @icon https://www.gogdb.org/static/img/sizes/gogdb_48x48.png
// @run-at document-end
// @match https://www.gog.com/game/*
// @grant unsafeWindow
// ==/UserScript==


var product_id = unsafeWindow.gogData.gameProductData.id;

var button_element = document.createElement("a");
button_element.innerHTML = '<img src="https://www.gogdb.org/static/img/gogdb_trans.svg" alt="" style="height: 15px; margin-right: 0.5em" referrerpolicy="no-referrer">GOG Database';
button_element.setAttribute("href", "https://www.gogdb.org/product/" + product_id);
button_element.className = "wishlist-btn";
button_element.setAttribute("style", "display: flex; flex-direction: row; justify-content: center; align-items: center");
button_element.setAttribute("target", "_blank");

var separator_element = document.createElement("div");
separator_element.setAttribute("style", "border-top: 1px solid rgba(0,0,0,.08); margin-top: 10px;");

var card_element = document.getElementsByClassName("socials")[0].parentNode;
card_element.appendChild(separator_element);
card_element.appendChild(button_element);

