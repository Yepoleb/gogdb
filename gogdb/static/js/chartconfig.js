function null_to_nan(value)
{
  if (value == null) {
    return NaN;
  }
  return value;
}

chart_init_called = false;
function init_chart()
{
  if (chart_init_called) {
      console.log("Chart already initialized");
      return;
  }
  chart_init_called = true;

  var pricehistory = JSON.parse(document.getElementById("pricehistory-json").innerHTML)
  pricehistory["values"] = pricehistory["values"].map(null_to_nan);

  var config = {
    type: "line",
    data: {
      labels: pricehistory["labels"],
      datasets: [{
        label: "Price",
        fill: false,
        steppedLine: true,
        borderColor: "rgb(241, 142, 0)",
        backgroundColor: "rgb(241, 142, 0)",
        data: pricehistory["values"],
      }]
    },
    options: {
      scales: {
        xAxes: [{
          type: "time",
          time: {
            tooltipFormat: "MMM D, YYYY",
          }
        }],
        yAxes: [{
          ticks: {
            beginAtZero: true,
            suggestedMax: Math.round(pricehistory["max"]) + 1
          }
        }]
      },
      legend: {
        display: false
      },
      maintainAspectRatio: false,
      layout: {
        padding: {
          top: 15
        }
      }
    }
  };

  var ctx = document.getElementById("chart-canvas");
  if (ctx != null) {
    window.myChart = new Chart(ctx, config);
  }
};

window.addEventListener("DOMContentLoaded", init_chart, false);
