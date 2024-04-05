$(document).ready(function () {
  let leftData;
  let rightData;
  let exData;
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
    // console.log("setting box shadow");
    // console.log(color);
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


    // console.log("setting checkpoints");
    for (let i = 0; i < 8; i++) {
      let checkpoint = i + 1
      let selector = div + " tr";
      let row = $(selector).eq(checkpoint);
      let valEl = row.find("td.checkpoint_val");
      let checkpointValue = checkpointsMap[checkpoint];

      // Reset board if nothing to show.
      if (!checkpointsMap[1]) {
        updateStatus(row);
        valEl.text(0);
        continue;
      }

      if (checkpointValue) {
        updateStatus(row, 1)
        valEl.text(formatTimestamp(checkpointValue));
      } else {
        // let now = new Date();
        // updateStatus(row, 0)
        // valEl.text(formatTimestamp(now));
        // return;
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
    // console.log("send_data")

    console.log(data);
    // console.log(data.left);
    // console.log(data.right);
    leftData = data.left;
    rightData = data.right;

    exData = {
      'car_id': 'CAR0001',
      'timestamp': 1712342069.785,
      'checkpoints': {
        1: 1707596526,
        2: 1707601628,
        3: 1707608768,
        4: 1707616369,
        5: 1707624172,
        6: 1707630592,
        7: 1707631702,
        8: 1707634954
      },
      'status': 1
    }
    // leftData = exData;
    // rightData = exData;

    setBoxShadow(carLeftDivId, baseStatus);
    setBoxShadow(carRightDivId, baseStatus);

    setPic(carLeftDivId, leftData.car_id);
    setPic(carRightDivId, rightData.car_id);

    setCheckpoints(carLeftDivId, leftData.checkpoints);
    setCheckpoints(carRightDivId, rightData.checkpoints);
  });

  setInterval(() => {
    if (leftData) {
      setCheckpoints(carLeftDivId, leftData.checkpoints);
    }
    if (rightData) {
      setCheckpoints(carRightDivId, rightData.checkpoints);
    }
  }, 100)

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
