// ==UserScript==
// @name GOG DB Integration
// @description Add a GOG DB link to the GOG store
// @version 0.7
// @author Yepoleb
// @license CC0
// @namespace https://gogdb.org
// @icon https://www.gogdb.org/static/img/sizes/gogdb_48x48.png
// @run-at document-end
// @match https://www.gog.com/game/*
// @match https://www.gog.com/*/game/*
// @grant unsafeWindow
// ==/UserScript==


var product_id = unsafeWindow.productcardData.cardProductId;

var gogdb_element = document.createElement("a");
gogdb_element.textContent = "GOG Database";
gogdb_element.setAttribute("href", "https://www.gogdb.org/product/" + product_id);
gogdb_element.className = "details__link";
gogdb_element.setAttribute("target", "_blank");

var separator_element = document.createTextNode(", ");

var links_xpath = "//a[@class='details__link' and contains(@href, 'gog.com/forum')]";
var links_element = document.evaluate(links_xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.parentNode;
links_element.appendChild(separator_element);
links_element.appendChild(gogdb_element);
