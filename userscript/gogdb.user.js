// ==UserScript==
// @name GOG DB Integration
// @description Add a GOG DB button to the GOG store
// @version 0.31
// @author Yepoleb
// @license CC0
// @namespace https://gogdb.org
// @icon https://www.gogdb.org/static/img/sizes/gogdb_48x48.png
// @run-at document-end
// @match https://www.gog.com/game/*
// @grant unsafeWindow
// ==/UserScript==


var product_id = unsafeWindow.productcardData.cardProductId;

var button_element = document.createElement("a");
button_element.innerHTML = '<img src="https://www.gogdb.org/static/img/gogdb_trans.svg" alt="" style="height: 15px; margin-right: 0.5em" referrerpolicy="no-referrer">GOG Database';
button_element.setAttribute("href", "https://www.gogdb.org/product/" + product_id);
button_element.className = "wishlist-btn details__row";
button_element.setAttribute("style", "display: flex; flex-direction: row; justify-content: center; align-items: center");
button_element.setAttribute("target", "_blank");

var separator_element = document.createElement("hr");
separator_element.className = "details__separator";

var card_element = document.getElementsByClassName("table__row details__row")[0];
var parent_card = card_element.parentNode;
parent_card.insertBefore(button_element, card_element);
parent_card.insertBefore(separator_element, card_element);
