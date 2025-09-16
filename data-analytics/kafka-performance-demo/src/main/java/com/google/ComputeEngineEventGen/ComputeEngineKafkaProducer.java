/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.google.ComputeEngineEventGen;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

import java.io.FileReader;
import java.io.IOException;
import java.util.Properties;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class ComputeEngineKafkaProducer implements AutoCloseable {

    private final KafkaProducer<String, String> producer;
    private final String topic;
    private final AtomicLong messageCount = new AtomicLong(0);
    private final AtomicLong totalSize = new AtomicLong(0);
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

    public ComputeEngineKafkaProducer() throws IOException {
        Properties props = new Properties();
        props.load(new FileReader("kafka-client.properties"));
        this.topic = System.getProperty("topic");
        String bootstrapServers = props.getProperty("bootstrap.servers");
        props.setProperty("bootstrap.servers", bootstrapServers);
        this.producer = new KafkaProducer<>(props);
        startScheduler();
    }

    private void startScheduler() {
        scheduler.scheduleAtFixedRate(() -> {
            long count = messageCount.getAndSet(0);
            long size = totalSize.getAndSet(0);
            if (count > 0) {
                System.out.println("--- Producer Stats (last 5 seconds) ---");
                System.out.println("Messages sent: " + count);
                System.out.println("Total size: " + size + " bytes");
                System.out.println("---------------------------------------");
            }
        }, 5, 5, TimeUnit.SECONDS);
    }

    public void sendMessage(String key, String value) {
        ProducerRecord<String, String> record = new ProducerRecord<>(this.topic, key, value);
        producer.send(record, (metadata, exception) -> {
            if (exception != null) {
                System.err.println("Error sending message to Kafka topic " + topic);
                exception.printStackTrace();
            } else {
                messageCount.incrementAndGet();
                totalSize.addAndGet(value.getBytes().length);
            }
        });
    }

    @Override
    public void close() {
        if (producer != null) {
            System.out.println("Flushing and closing KafkaProducer for topic: " + topic);
            producer.flush();
            producer.close();
        }
        scheduler.shutdown();
    }
}