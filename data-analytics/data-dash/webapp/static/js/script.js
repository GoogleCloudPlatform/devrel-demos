$(document).ready(function() {
  const baseColor = "yellow"
  const carLeftDivId = "#car_1"
  const carRightDivId = "#car_2"
  const statusClasses = ["race-going", "race-over", "race-failed"]

  var socket = io();

  function setBoxShadow(div, color) {
    console.log("setting box shaddow");
    console.log(color);
    statusClasses.forEach(c => {
      $(div).removeClass(c);
    })
    if (color === "yellow") {
      $(div).addClass("race-going")
    }
    if (color === "green") {
      $(div).addClass("race-over")
    }
    if (color === "red") {
      $(div).addClass("race-failed")
    }
  }
  function setPic(div, id) {
    // $(div + " .img").css("background-image", `url("https://storage.googleapis.com/data-analytics-demos/next2024/cars/${id}.jpg")`);
  }
  socket.on('connect', function() {
    setBoxShadow(carLeftDivId, baseColor);
    setBoxShadow(carRightDivId, baseColor);
  });
  socket.on('set_pictures', function(data) {
    setPic(carLeftDivId, data.left_id);
    setPic(carRightDivId, data.right_id);
  });
  socket.on('set_status', function(data) {
    console.log(data)
    setBoxShadow(data.left_color);
    setBoxShadow(data.left_color);
    if (data.left_data !== null) {
      document.getElementById("stats").textContent=data.left_data;
    }
    if (data.right_data !== null) {
      document.getElementById("stats2").textContent=data.right_data;
    }
  })
});