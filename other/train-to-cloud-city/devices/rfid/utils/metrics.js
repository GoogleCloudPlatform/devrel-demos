const { PubSub } = require("@google-cloud/pubsub");

const pubSubClient = new PubSub();

let queuedMetricsToPublish = [];

/**
 * queueMessageToPublish
 * ---------------------------
 * Queue up metrics to publish while game is going on
 */ 
function queueMessageToPublish(topic, data) {
  const dataBuffer = Buffer.from(JSON.stringify(data));
  queuedMetricsToPublish.push({ topic, data: dataBuffer, timestamp: Date.now() });
}

/**
 * publishQueuedMessages
 * ---------------------------
 * As long as there are items in the queue to publish
 * continue pushing items up to google-cloud pubsub
 */ 
(async function publishQueuedMessages() {
  console.log("----- finding metrics ...");
  setInterval(() => {
    queuedMetricsToPublish?.forEach(async (metric) => {
      try {
        const messageId = await pubSubClient.topic(metric?.topic).publishMessage({ data: metric?.data, timestamp: metric?.timestamp });
        console.log(messageId);
        console.log(`Message ${messageId} published.`);
        // clear published metrics
        queuedMetricsToPublish = [];
      } catch (error) {
        console.error(`Received error while publishing: ${error.message}`);
        process.exitCode = 1;
      }
    });
  }, 500);
})();

module.exports = { queueMessageToPublish };

