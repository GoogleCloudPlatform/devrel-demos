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
  const publishTimeBuffer = Buffer.from(
    JSON.stringify({ timestamp: Date.now() }),
  );

  queuedMetricsToPublish.push({
    topic,
    publishTime: publishTimeBuffer,
    data: dataBuffer,
  });
}

/**
 * publishQueuedMessages
 * ---------------------------
 * As long as there are items in the queue to publish
 * continue pushing items up to google-cloud pubsub
 */
(async function publishQueuedMessages() {
  setInterval(() => {
    queuedMetricsToPublish?.forEach(async (metrics) => {
      const topicBuffer = Buffer.from(JSON.stringify(metrics?.topic));
      try {
        const messageId = await pubSubClient
          .topic(metrics?.topic)
          .publishMessage({
            data: metrics?.data,
            topic: topicBuffer,
            timestamp: metrics?.publishTime,
          });
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
