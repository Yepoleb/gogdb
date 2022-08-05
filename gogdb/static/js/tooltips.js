function initChart(chart) {
    // Constants
    let tooltip_margin = 5;  // How far away from the dot the tooltip should appear in px
    let tooltip_timeout = 500;  // How long the tooltip will linger after the mouse moved away

    let chart_svg = chart.getSVGDocument();
    let chart_root = chart_svg.getElementsByTagName("svg")[0]

    // Build tooltip element and append to chart parent
    // Parent element needs to be `position: relative` for the positioning to work
    let tooltip_el = document.createElement("div");
    tooltip_el.className = "tooltip";
    let date_el = document.createElement("span");
    date_el.className = "tooltip-date";
    let price_el = document.createElement("span");
    price_el.className = "tooltip-price";
    tooltip_el.appendChild(date_el);
    tooltip_el.appendChild(document.createElement("br"));
    tooltip_el.appendChild(price_el);
    chart.parentElement.appendChild(tooltip_el);

    // Timeout ID for the tooltip fadeout
    let tooltip_timeout_id = 0;

    let dots = chart_svg.getElementsByClassName("dots");
    for (let dot of dots) {
        let combined_val = dot.getElementsByClassName("value")[0].textContent;
        let [date_val, price_val] = combined_val.split(": ", 2);
        dot.addEventListener("mouseenter", (event) => {
            if (tooltip_timeout_id != 0) {
                clearTimeout(tooltip_timeout_id);
                tooltip_timeout_id = 0;
            }
            tooltip_el.style.display = "unset";
            date_el.textContent = date_val;
            price_el.textContent = price_val;

            // Position is calculated relative to the left upper corner of the chart
            let chart_bbox = chart_root.getBoundingClientRect();
            let dot_bbox = dot.getBoundingClientRect();
            let tooltip_bbox = tooltip_el.getBoundingClientRect();

            let dot_center_y = (dot_bbox.top + dot_bbox.bottom) / 2;
            let tooltip_height = tooltip_bbox.top - tooltip_bbox.bottom;
            let tooltip_width = tooltip_bbox.right - tooltip_bbox.left;

            let pos_y = dot_center_y + tooltip_height / 2;
            tooltip_el.style.top = pos_y.toString() + "px";
            // Dots in the left half have their tooltips on the right side,
            // dots in the right have them on the left side
            if (dot_bbox.left < (chart_bbox.right / 2)) {
                let pos_x = dot_bbox.right + tooltip_margin;
                tooltip_el.style.left = pos_x.toString() + "px";
            } else {
                let pos_x = dot_bbox.left - tooltip_width - tooltip_margin;
                tooltip_el.style.left = pos_x.toString() + "px";
            }
        });
        dot.addEventListener("mouseleave", (event) => {
            if (tooltip_timeout_id != 0) {
                clearTimeout(tooltip_timeout_id);
            }
            tooltip_timeout_id = setTimeout(() => {
                tooltip_el.style.display = "none";
            }, tooltip_timeout);
        });
    }
}

window.addEventListener("load", (event) => {
    let charts = document.querySelectorAll(".chart-object");
    if (charts !== null) {
        for (let chart of charts) {
            initChart(chart);
        }
    }
});
