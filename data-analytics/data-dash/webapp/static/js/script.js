$(document).ready(function () {
  const baseStatus = "0";
  const carLeftDivId = "#car_1";
  const carRightDivId = "#car_2";
  const statusClassesMap = {
    0: "race-going",
    1: "race-over",
    2: "race-failed",
  };

  var socket = io();

  function setBoxShadow(div, status) {
    var color = statusClassesMap[status];
    console.log("setting box shadow");
    console.log(color);
    Object.keys(statusClassesMap).forEach((c) => {
      $(div).removeClass(statusClassesMap[c]);
    });
    $(div).addClass(color);
  }
  function setPic(div, id) {
    $(div + " .img").css(
      "background-image",
      `url("https://storage.googleapis.com/data-analytics-demos/next2024/cars/${id}.jpg")`,
    );
  }

  socket.on("connect", function () {
    setBoxShadow(carLeftDivId, baseStatus);
    setBoxShadow(carRightDivId, baseStatus);
  });
  socket.on("send_data", function (data) {
    console.log(data.left);
    console.log(data.right);
    setBoxShadow(carLeftDivId, baseStatus);
    setBoxShadow(carRightDivId, baseStatus);
    setPic(carLeftDivId, data.left.car_id);
    setPic(carRightDivId, data.right.car_id);
  });
  // socket.on('set_pictures', function(data) {
  //   setPic(carLeftDivId, data.left.car_id);
  //   setPic(carRightDivId, data.right.car_id);
  // });
  // socket.on('set_status', function(data) {
  //   console.log(data)
  //   setBoxShadow(data.left_color);
  //   setBoxShadow(data.left_color);
  //   if (data.left_data !== null) {
  //     document.getElementById("stats").textContent=data.left_data;
  //   }
  //   if (data.right_data !== null) {
  //     document.getElementById("stats2").textContent=data.right_data;
  //   }
  // })
});
