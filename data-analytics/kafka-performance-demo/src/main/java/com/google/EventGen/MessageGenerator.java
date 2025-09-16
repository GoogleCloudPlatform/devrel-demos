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
package com.google.EventGen;

import com.google.EventGen.KafkaScenario;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.LinkedHashMap; // For preserving order in summary map
import net.datafaker.Faker;

public class MessageGenerator {
    private int messageCounter = 0;
    private final Random random = new Random();
    private final Faker faker = new Faker(random);
    // Pre-load comments to avoid regenerating them for every message
    private static final Map<String, List<String>> sampleComments = EcommerceEvents.getSampleComments();
    private static final List<String> transactionComments = sampleComments.get("Transaction");
    private static final List<String> merchantActionComments = sampleComments.get("MerchantAction");

    private static final int MAX_REUSABLE_USER_IDS = 10; // Max number of user IDs to keep for potential reuse
    private static final double CHANCE_TO_REUSE_USER_ID = 0.3; // 30% chance to reuse an existing userId
    private final List<String> reusableUserIds = new ArrayList<>();

    // Functional interface for processing generated messages
    @FunctionalInterface
    public static interface MessageProcessor {
        void process(Object message, long sizeBytes) throws Exception;
    }

    public List<Object> generateEventsForScenario(KafkaScenario scenario) {
        switch (scenario) {
            case LARGE_ANALYTICAL_DATA:
                return generateSessionEvents();
            default:
                return generateSessionEvents();
        }
    }

    public List<Object> generateSessionEvents() {
        List<Object> sessionEvents = new ArrayList<>();
        String userId;

        if (!reusableUserIds.isEmpty() && random.nextDouble() < CHANCE_TO_REUSE_USER_ID) {
            userId = reusableUserIds.get(random.nextInt(reusableUserIds.size()));
        } else {
            userId = faker.internet().uuid();
            if (reusableUserIds.size() >= MAX_REUSABLE_USER_IDS) {
                reusableUserIds.remove(0);
            }
            reusableUserIds.add(userId);
        }
        String sessionId = faker.internet().uuid();
        LocalDateTime sessionStartTime = LocalDateTime.now().minusMinutes(random.nextInt(1440));
        LocalDateTime currentEventTime = sessionStartTime;

        int numInteractions = 1 + random.nextInt(5);
        for (int i = 0; i < numInteractions; i++) {
            currentEventTime = currentEventTime.plusSeconds(random.nextInt(120) + 10);
            EcommerceEvents.UserInteractionEvent interaction = EcommerceEvents.generateUserInteractionEvent(faker, random, sessionId, userId, currentEventTime);
            sessionEvents.add(interaction);
            messageCounter++;
        }

        int numTransactions = random.nextInt(3);
        List<String> transactionIdsThisSession = new ArrayList<>();

        for (int i = 0; i < numTransactions; i++) {
            currentEventTime = currentEventTime.plusMinutes(random.nextInt(10) + 1);
            EcommerceEvents.TransactionEvent transaction = EcommerceEvents.generateTransactionEvent(faker, random, transactionComments, sessionId, userId, currentEventTime);
            sessionEvents.add(transaction);
            transactionIdsThisSession.add(transaction.getTransactionId());
            messageCounter++;

            if (random.nextDouble() < 0.7) {
                int numMerchantActions = 1 + random.nextInt(2);
                for (int j = 0; j < numMerchantActions; j++) {
                    currentEventTime = currentEventTime.plusMinutes(random.nextInt(20) + 2);
                    EcommerceEvents.MerchantActionEvent merchantAction = EcommerceEvents.generateMerchantActionEvent(
                        faker, random, merchantActionComments,
                        transaction.getTransactionId(),
                        userId,
                        currentEventTime
                    );
                    sessionEvents.add(merchantAction);
                    messageCounter++;
                }
            }
        }
        return sessionEvents;
    }

    public long getMessageSizeBytes(Object message) {
        if (message == null || message.toString() == null) {
            return 0;
        }
        return message.toString().getBytes(StandardCharsets.UTF_8).length;
    }

    public Map<String, Object> generateAndProcessBatch(int numIterations, int targetSessionsPerIteration, int targetBytesPerIteration, KafkaScenario scenario, MessageProcessor processor) throws Exception {
        long totalMessagesGenerated = 0;
        long totalBytesGenerated = 0;
        long batchStartTime = System.currentTimeMillis();

        for (int currentIteration = 0; currentIteration < numIterations; currentIteration++) {
            for (int sessionInIteration = 0; sessionInIteration < targetSessionsPerIteration; sessionInIteration++) {
                List<Object> sessionMessages = generateEventsForScenario(scenario);
                for (Object message : sessionMessages) {
                    long messageSizeBytes = getMessageSizeBytes(message); 
                    processor.process(message, messageSizeBytes); 
                    totalMessagesGenerated++;
                    totalBytesGenerated += messageSizeBytes;
                }
            }
        }

        long actualDurationMs = System.currentTimeMillis() - batchStartTime;
        return printBatchSummary(numIterations, targetSessionsPerIteration, targetBytesPerIteration,
                          totalMessagesGenerated, totalBytesGenerated, actualDurationMs);
    }

    private Map<String, Object> printBatchSummary(int targetIterations, int targetSessionsPerIteration, int targetBytesPerIteration,
                                                  long totalMessagesGenerated, long totalBytesGenerated, long actualDurationMs) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("targetIterations", targetIterations);
        summary.put("actualDurationSeconds", actualDurationMs / 1000.0);
        summary.put("targetSessionsPerIteration", targetSessionsPerIteration);
        summary.put("targetGeneratorBytesPerIteration", targetBytesPerIteration);
        summary.put("totalMessagesGenerated", totalMessagesGenerated);
        summary.put("totalBytesGenerated", totalBytesGenerated);
        summary.put("totalKilobytesGenerated", totalBytesGenerated / 1024.0);
        summary.put("totalMegabytesGenerated", totalBytesGenerated / (1024.0 * 1024.0));

        if (actualDurationMs > 0) {
            double actualMessagesPerSecond = (double) totalMessagesGenerated * 1000.0 / actualDurationMs;
            double actualBytesPerSecond = (double) totalBytesGenerated * 1000.0 / actualDurationMs;
            summary.put("actualMessagesPerSecond", actualMessagesPerSecond);
            summary.put("actualBytesPerSecond", actualBytesPerSecond);
            summary.put("actualKilobytesPerSecond", actualBytesPerSecond / 1024.0);
            summary.put("actualMegabytesPerSecond", actualBytesPerSecond / (1024.0 * 1024.0));
        } else {
            summary.put("actualMessagesPerSecond", 0.0);
            summary.put("actualBytesPerSecond", 0.0);
            summary.put("actualKilobytesPerSecond", 0.0);
            summary.put("actualMegabytesPerSecond", 0.0);
        }

        if (totalMessagesGenerated > 0) {
            double avgMsgSize = (double) totalBytesGenerated / totalMessagesGenerated;
            summary.put("averageMessageSizeBytes", avgMsgSize);
        } else {
            summary.put("averageMessageSizeBytes", 0.0);
        }
        return summary;
    }
}
