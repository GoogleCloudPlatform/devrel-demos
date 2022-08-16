const functions = require("@google-cloud/functions-framework");
const util = require("util");

// note: isWarm is "undefined" until startup() starts executing
// then isWarm becomes a Promise which is never falsey (more below)
var isWarm = startup();

async function startup() {
  console.log("🥶 i'm a cold start");

  // 10 seconds seems to work best for this demo
  await sleep(10000);

  // when setTimeout is finished, have it resume with "I'm ready now"
  // just like any other real world connection
  console.log("I'm ready now");

  // the issue w returning boolean here is that at this point
  // isWarm = Promise { <pending> }
  // so it is always "truthy"
  // returning a string is a much better way to verify the work has been completed
  // and is closer to a real world scenario (e.g. approximating the data you get from an API)
  return "ready";
}

// simulating a long API call or slow network connection
function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

functions.http("cold-starts", async (req, res) => {
  // This next line allows you to check whether Promise is pending or is fulfilled
  // if pending, this evaluates to `Promise { <pending> }`
  // if fulfilled, this evaluates to `Promise { 'ready' }`
  // note: isWarm is a Promise, not a string
  var isStatusPending = util.inspect(isWarm).includes("pending");

  // Use stdout to see in Cloud Logging which revision & instanceId is handling the request
  console.log("request received...");

  if (isStatusPending) {
    console.log("I'm still a 🥶 start.");

    // javascript notes:
    // 1) you must use `await isWarm` and not `await isWarm()`
    // because it's a Promise, not a Function.
    // 2) to get the contents "ready" you have to resolve the Promise
    // this next line is the equivalent of calling .then(), so it goes onto "I'm ready now"
    var result = await isWarm;
    console.log("now I'm warmed up 🥰!");
  } else {
    // see note above re javascript
    var result = await isWarm;
    // and you'll see in the logs "I'm awake now" is immediately followed by
    // "I'm a warm instance", where both have the same instanceId
    // All the other "I'm ready now" logs all have different instanceIds
    console.log("🥰 I'm a warm instance.");
  }

  // and either 🥶 or 🥰 our request is completed!
  let message = req.query.message || req.body.message || "Request completed!";
  res.status(200).send(message);
});
