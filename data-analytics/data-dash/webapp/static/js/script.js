$(document).ready(function () {
  let leftData;
  let rightData;
  let exData;
  const baseStatus = "0";
  const carLeftDivId = "#car_1";
  const carRightDivId = "#car_2";
  const statusClassesMap = {
    0: "race-going",
    1: "race-win",
    2: "race-lose",
    3: "checkpoint",
  };

  var socket = io();

  function setBoxShadow(div, status) {
    updateStatus(div, status)
  }

  function updateStatus(selector, status) {
    let el = $(selector);
    Object.values(statusClassesMap).forEach(s => {
      el.removeClass(s);
    });

    if (status) {
      el.addClass(statusClassesMap[status]);
    }
  }

  function setCheckpoints(div, checkpointsMap) {
    for (let i = 0; i < 8; i++) {
      let checkpoint = i + 1
      let selector = div + " tr";
      let row = $(selector).eq(checkpoint);
      let valEl = row.find("td.checkpoint_val");
      let checkpointValue = checkpointsMap[checkpoint];

      // Reset board if nothing to show.
      if (!checkpointValue) {
        updateStatus(row);
        valEl.text(0);
        continue;
      }

      if (checkpointValue) {
        updateStatus(row, 3)
        valEl.text(formatTimestamp(checkpointValue));
      } 
    }
  }

  function formatTimestamp(timestamp) {
    // Create a Date object from the timestamp
    const date = new Date(timestamp);

    // Extract components for formatting
    let hours = date.getHours().toString().padStart(2, '0');
    hours = hours % 12 || 12
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    const milliseconds = date.getMilliseconds().toString().padStart(3, '0');

    // Construct the formatted time string
    return `${hours}:${minutes}:${seconds}:${milliseconds}`;
  }

  function setPic(div, id) {
    $(div + " .img").css(
        "background-image",
        `url("https://storage.googleapis.com/data-analytics-demos/next2024/cars/${id}.png")`,
    );
  }

  socket.on("connect", function () {
    console.log("connect")
    setBoxShadow(carLeftDivId, baseStatus);
    setBoxShadow(carRightDivId, baseStatus);
  });
  socket.on("send_data", function (data) {
    console.log("data received")
    leftData = data.left;
    rightData = data.right;

    setBoxShadow(carLeftDivId, leftData.status);
    setBoxShadow(carRightDivId, rightData.status);
    
    console.log("LEFT DATA:")
    console.log(leftData)
    setPic(carLeftDivId, leftData.car_id);

    console.log("RIGHT DATA:")
    console.log(rightData)
    setPic(carRightDivId, rightData.car_id);

    setCheckpoints(carLeftDivId, leftData.checkpoints);
    setCheckpoints(carRightDivId, rightData.checkpoints);
  });

  socket.on('disconnect', function() {
    console.log('Disconnected from server');

    // Attempt reconnection every 3 seconds
    setTimeout(function() {
        socket.connect();
    }, 3000); 
});

  socket.on('set_default', function(data) {
    console.log("setting default")
    setPic(carLeftDivId, data.left_id);
    setPic(carRightDivId, data.right_id);
  });
});
