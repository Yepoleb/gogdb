function history_date(entry)
{
  return moment(entry.date);
}

function history_price(entry)
{
  return entry.price_final;
}

function history_price_float(entry)
{
  return parseFloat(entry.price_final);
}

chart_init_called = false;
function init_chart()
{
  if (chart_init_called) {
      console.log("chart init double");
      return;
  }
  chart_init_called = true;
  var max_price = Math.max.apply(null, pricehistory.map(history_price_float))

  var config = {
    type: "line",
    data: {
      labels: pricehistory.map(history_date),
      datasets: [{
        label: "Price",
        fill: false,
        steppedLine: true,
        borderColor: "rgb(241, 142, 0)",
        backgroundColor: "rgb(241, 142, 0)",
        data: pricehistory.map(history_price),
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
            suggestedMax: Math.round(max_price) + 1
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

  var ctx = document.getElementById("chart-canvas").getContext("2d");
  window.myChart = new Chart(ctx, config);
};

window.addEventListener("DOMContentLoaded", init_chart, false);
