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

import com.google.EventGen.KafkaScenario;
import com.google.EventGen.MessageGenerator;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.*;
import java.util.concurrent.atomic.LongAdder;

public class ComputeEngineEventGen {

    private static volatile int targetNumThreads;
    private static final ConcurrentHashMap<Long, LongAdder> messageCounts = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<Long, LongAdder> byteCounts = new ConcurrentHashMap<>();

    public static void main(String[] args) throws Exception {
        // --- Configuration via System Properties (-Dkey=value) ---
        KafkaScenario scenario = KafkaScenario.fromString(System.getProperty("scenario", "DEFAULT"));

        targetNumThreads = Integer.parseInt(System.getProperty("numThreads", "1"));
        System.out.println("Starting with " + targetNumThreads + " generator threads.");

        ThreadPoolExecutor executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(targetNumThreads);
        List<Future<?>> futures = new ArrayList<>();

        ScheduledExecutorService statsScheduler = Executors.newSingleThreadScheduledExecutor();
        statsScheduler.scheduleAtFixedRate(() -> {
            System.out.println("--- 5 Second Stats ---");
            long totalMessages = 0;
            long totalBytes = 0;
            for (long threadId : messageCounts.keySet()) {
                long messages = messageCounts.get(threadId).sumThenReset();
                long bytes = byteCounts.get(threadId).sumThenReset();
                totalMessages += messages;
                totalBytes += bytes;
                System.out.printf("Thread %d: %.2f msg/s, %.2f MB/s%n",
                        threadId,
                        (double) messages / 5.0,
                        (double) bytes / (5.0 * 1024 * 1024));
            }
            System.out.printf("Total: %.2f msg/s, %.2f MB/s%n",
                    (double) totalMessages / 5.0,
                    (double) totalBytes / (5.0 * 1024 * 1024));
            System.out.println("----------------------");
        }, 5, 5, TimeUnit.SECONDS);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Shutdown hook triggered.");
            statsScheduler.shutdown();
            executor.shutdownNow();
            try {
                if (!executor.awaitTermination(60, TimeUnit.SECONDS)) {
                    System.err.println("Executor did not terminate");
                }
            } catch (InterruptedException e) {
                executor.shutdownNow();
            }
        }));

        startInputListener();

        // Start initial tasks
        for (int i = 0; i < executor.getCorePoolSize(); i++) {
            futures.add(submitNewTask(executor, scenario));
        }

        while (true) {
            if (executor.getCorePoolSize() != targetNumThreads) {
                System.out.println("Adjusting number of threads to " + targetNumThreads);
                if (targetNumThreads > executor.getCorePoolSize()) {
                    executor.setMaximumPoolSize(targetNumThreads);
                    executor.setCorePoolSize(targetNumThreads);
                } else {
                    executor.setCorePoolSize(targetNumThreads);
                    executor.setMaximumPoolSize(targetNumThreads);
                }
            }

            // Add new tasks if thread pool has grown
            while (futures.size() < executor.getCorePoolSize()) {
                System.out.println("Adding a new task to the pool.");
                futures.add(submitNewTask(executor, scenario));
            }

            // Cancel tasks if thread pool has shrunk
            while (futures.size() > executor.getCorePoolSize()) {
                System.out.println("Removing a task from the pool.");
                Future<?> future = futures.remove(futures.size() - 1);
                future.cancel(true);
            }

            Thread.sleep(1000);
        }
    }

    private static void startInputListener() {
        Thread inputListenerThread = new Thread(() -> {
            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
            System.out.println("Enter target number of threads and press Enter (or 'q' to quit):");
            while (true) {
                try {
                    String line = reader.readLine();
                    if (line != null) {
                        if ("q".equalsIgnoreCase(line.trim())) {
                            System.out.println("Exiting...");
                            System.exit(0);
                        }
                        try {
                            int newNumThreads = Integer.parseInt(line.trim());
                            if (newNumThreads >= 0) {
                                targetNumThreads = newNumThreads;
                                System.out.println("Target number of threads set to " + newNumThreads);
                            } else {
                                System.err.println("Number of threads must be non-negative.");
                            }
                        } catch (NumberFormatException e) {
                            System.err.println("Invalid input. Please enter a number or 'q'.");
                        }
                        System.out.println("Enter target number of threads and press Enter (or 'q' to quit):");
                    }
                } catch (IOException e) {
                    break;
                }
            }
        });
        inputListenerThread.setDaemon(true);
        inputListenerThread.start();
    }

    private static Future<?> submitNewTask(ExecutorService executor,
                                           KafkaScenario scenario) {
        return executor.submit(() -> {
            long threadId = Thread.currentThread().getId();
            messageCounts.putIfAbsent(threadId, new LongAdder());
            byteCounts.putIfAbsent(threadId, new LongAdder());

            Properties props = new Properties();
            try {
                props.load(new FileReader("kafka-client.properties"));
                String bootstrapServers = props.getProperty("bootstrap.servers");
                props.setProperty("bootstrap.servers", bootstrapServers);
            } catch (IOException e) {
                e.printStackTrace();
                return; // exit task
            }

            try (KafkaProducer<String, String> producer = new KafkaProducer<>(props)) {
                MessageGenerator messageGenerator = new MessageGenerator();
                String topic = System.getProperty("topic");
                while (!Thread.currentThread().isInterrupted()) {
                    List<Object> sessionEvents = messageGenerator.generateSessionEvents();
                    for (Object event : sessionEvents) {
                        String message = event.toString();
                        byte[] messageBytes = message.getBytes();
                        producer.send(new ProducerRecord<>(topic, null, message));
                        messageCounts.get(threadId).increment();
                        byteCounts.get(threadId).add(messageBytes.length);
                    }
                }
            } catch (Exception e) {
                if (!(e instanceof InterruptedException)) {
                    e.printStackTrace();
                }
            } finally {
                messageCounts.remove(threadId);
                byteCounts.remove(threadId);
            }
        });
    }
}
