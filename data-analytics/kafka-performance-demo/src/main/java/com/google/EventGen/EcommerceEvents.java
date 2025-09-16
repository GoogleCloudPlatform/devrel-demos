package com.google.EventGen;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Arrays;
import java.util.Map;
import java.util.Random;
import java.util.StringJoiner;
import java.text.SimpleDateFormat;
import java.util.stream.Collectors;
import net.datafaker.Faker;

public class EcommerceEvents {

    private static String escapeJson(String s) {
        if (s == null) {
            return ""; // Should be handled by caller to output literal null
        }
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\b", "\b")
                .replace("\f", "\f")
                .replace("\n", "\n")
                .replace("\r", "\r")
                .replace("\t", "\t");
    }

    private static final Random commentRandom = new Random();

    private static List<String> generateTransactionComments(Faker faker) {
        List<String> comments = new ArrayList<>();
        // Using DataFaker for more varied and realistic-sounding comments
        String[] prefixes = {faker.options().option("Please","Kindly","Ensure","Make sure to","Requesting that you"), "I'd appreciate it if you could", "Could you please"};
        String[] actions = {faker.verb().base() + " the package", faker.verb().base() + " the item", "place the order", "ship the goods"};
        String[] locations = {"by the " + faker.address().streetSuffix().toLowerCase() + " door", "behind the " + faker.animal().name().toLowerCase() + " gate", "with the " + faker.name().firstName(), "at the reception", "in the " + faker.color().name() + " mailbox", "near the " + faker.food().fruit().toLowerCase() + " plant"};
        String[] conditions = {"if I'm not home", "for safer delivery", "to avoid " + faker.hacker().noun().toLowerCase(), "as I'll be out", "thank you!", "much appreciated."}; // Note: faker.hacker().noun() will be the same for all if faker is static and this method is called once.
        String[] giftNotes = {"Happy " + faker.options().option("Birthday","Anniversary","Holidays") + "!", "Congratulations on your " + faker.options().option("new job","graduation","baby") + "!", "With love from " + faker.name().firstName(), "Thinking of you, " + faker.name().firstName() + "."};
        SimpleDateFormat dateFormat = new SimpleDateFormat("EEE MMM dd");
        String[] specialInstructions = {"Gift wrap this item in " + faker.color().name() + " paper.", "Include a gift note: '" + faker.lorem().sentence(3) + "'", "Fragile, handle with care like a " + faker.animal().name() + ".", "Urgent delivery needed by " + dateFormat.format(faker.date().future(1, java.util.concurrent.TimeUnit.DAYS)) + ".", "Call " + faker.phoneNumber().cellPhone() + " upon arrival."};

        int count = 50 + commentRandom.nextInt(51); // 50 to 100 comments
        for (int i = 0; i < count; i++) {
            StringBuilder sb = new StringBuilder();
            int type = commentRandom.nextInt(4);
            if (type == 0) { // Delivery instruction
                sb.append(prefixes[commentRandom.nextInt(prefixes.length)]).append(" ");
                sb.append(actions[commentRandom.nextInt(actions.length)]).append(" ");
                sb.append(locations[commentRandom.nextInt(locations.length)]);
                if (commentRandom.nextBoolean()) {
                    sb.append(" ").append(conditions[commentRandom.nextInt(conditions.length)]);
                }
            } else if (type == 1) { // Gift note
                sb.append("Gift note: ").append(giftNotes[commentRandom.nextInt(giftNotes.length)]);
                if (commentRandom.nextBoolean()) {
                    sb.append(" From: ").append(faker.name().firstName()); // Replaced hardcoded array
                }
            } else if (type == 2) { // Special instruction
                sb.append(specialInstructions[commentRandom.nextInt(specialInstructions.length)]);
                if (commentRandom.nextBoolean() && sb.toString().contains("gift note")) {
                    sb.append(" Note: '").append(giftNotes[commentRandom.nextInt(giftNotes.length)]).append("'");
                }
            } else { // Simple request
                sb.append(prefixes[commentRandom.nextInt(prefixes.length)]).append(" handle with extra care, it's a gift for ").append(faker.name().firstName()).append("."); // Used faker for name
            }
            comments.add(sb.toString().trim() + " (Order #" + (1000 + i) + ")");
        }
        return comments;
    }

    private static List<String> generateMerchantActionComments(Faker faker) {
        List<String> comments = new ArrayList<>();
        String[] customerAdvised = {"Customer " + faker.verb().past() , "User " + faker.verb().past(), "Client " + faker.verb().past(), "Buyer " + faker.verb().past()};
        String[] actionTaken = {"we should " + faker.verb().base(), "to " + faker.verb().base(), "that we need to " + faker.verb().base(), "the team will " + faker.verb().base()};
        String[] deliveryActions = {"leave the package by the " + faker.address().streetSuffix().toLowerCase(), "place item behind the " + faker.animal().name().toLowerCase() + " gate", "contact " + faker.name().firstName() + " before delivery", "ensure signature on receipt from " + faker.name().fullName()};
        String[] reasons = {"for safer delivery of " + faker.commerce().productName(), "due to " + faker.weather().description().toLowerCase(), "as per instructions from " + faker.company().name(), "to confirm receipt by " + faker.name().lastName()};
        String[] internalNotes = {"Followed up with customer " + faker.name().fullName() + ".", "Logistics team at " + faker.company().bs() + " notified.", "Inventory for " + faker.commerce().productName() + " adjusted.", "Refund processed as per policy " + faker.idNumber().valid() + ".", "Shipping label " + faker.app().version() + " generated."};
        String[] resolutions = {"Issue with " + faker.hacker().noun() + " resolved.", "Awaiting customer feedback on " + faker.book().title() + ".", "Escalated to Tier 2 support agent " + faker.name().firstName() + ".", "Partial refund of " + faker.commerce().price() + " offered.", "Replacement " + faker.commerce().productName() + " shipped via " + faker.company().name() + "."};

        int count = 50 + commentRandom.nextInt(51); // 50 to 100 comments
        for (int i = 0; i < count; i++) {
            StringBuilder sb = new StringBuilder();
            int type = commentRandom.nextInt(4);
            if (type == 0) { // Customer instruction relay
                sb.append(customerAdvised[commentRandom.nextInt(customerAdvised.length)]).append(" ");
                sb.append(actionTaken[commentRandom.nextInt(actionTaken.length)]).append(" ");
                sb.append(deliveryActions[commentRandom.nextInt(deliveryActions.length)]);
                if (commentRandom.nextBoolean()) {
                    sb.append(" ").append(reasons[commentRandom.nextInt(reasons.length)]);
                }
            } else if (type == 1) { // Internal note
                sb.append("Internal Note: ").append(internalNotes[commentRandom.nextInt(internalNotes.length)]);
                if (commentRandom.nextBoolean()) {
                    sb.append(" Ref: Ticket #").append(7000 + i);
                }
            } else if (type == 2) { // Resolution status
                sb.append(resolutions[commentRandom.nextInt(resolutions.length)]);
                if (commentRandom.nextBoolean()) {
                    sb.append(" Contacted user via email.");
                }
            } else { // General merchant action
                sb.append("Action taken: ").append(faker.options().option(
                    "Verified payment for " + faker.commerce().productName(),
                    "Updated shipping address to " + faker.address().streetAddress(),
                    "Processed return request for item " + faker.commerce().promotionCode().split(",")[0],
                    "Applied discount code " + faker.commerce().promotionCode() + " manually for " + faker.name().firstName()
                )).append(" for order ").append(faker.idNumber().valid().substring(0,8));
            }
            comments.add(sb.toString().trim() + " (Staff ID: " + (100 + i % 10) + ")");
        }
        return comments;
    }

    /**
     * Generates a map of sample comments for different event types.
     * @return A Map where keys are "Transaction" or "MerchantAction" and
     *         values are lists of sample comment strings.
     */
    public static Map<String, List<String>> getSampleComments() {
        Map<String, List<String>> sampleComments = new HashMap<>();
        // Create a local Faker instance for comment generation to ensure variety if getSampleComments is called multiple times.
        Faker localFakerForComments = new Faker(commentRandom);
        sampleComments.put("Transaction", generateTransactionComments(localFakerForComments));
        sampleComments.put("MerchantAction", generateMerchantActionComments(localFakerForComments));
        return sampleComments;
    }

    private static <T> T randomElement(List<T> list, Random random) {
        if (list == null || list.isEmpty()) {
            return null;
        }
        return list.get(random.nextInt(list.size()));
    }

    private static String generateInternalNoteForMerchantAction(Faker faker, Random random) {
        String[] noteTemplates = {
            "Followed up with customer " + faker.name().fullName() + " regarding order #" + faker.idNumber().valid().substring(0, 6) + ".",
            "Logistics team (" + faker.company().catchPhrase() + " Dept) notified for dispatch of item: " + faker.commerce().productName() + ".",
            "Inventory for " + faker.commerce().productName() + " (SKU: " + faker.commerce().promotionCode().split(",")[0] + ") double-checked and confirmed available.",
            "Refund of " + faker.money().currencyCode() + " " + String.format("%.2f", faker.number().randomDouble(2, 10, 200)) + " processed for transaction ID: " + faker.finance().creditCard() + ". Policy ref: POL-" + faker.number().digits(4) + ".",
            "Shipping label " + faker.app().version() + "-" + faker.random().hex(8) + " generated for carrier " + faker.company().name() + ".",
            "Customer query regarding " + faker.commerce().material() + " " + faker.commerce().productName() + " escalated to " + faker.commerce().department() + " team. Ticket ID: T" + faker.number().digits(7) + ".",
            "Payment verification for order #" + faker.idNumber().valid().substring(0, 6) + " completed via " + faker.business().creditCardType() + ". Auth code: " + faker.random().hex(6).toUpperCase() + ".",
            "Scheduled a callback for " + faker.date().future(5, java.util.concurrent.TimeUnit.DAYS).toInstant().atZone(ZoneId.systemDefault()).toLocalDate() + " with " + faker.name().firstName() + " to discuss " + faker.hacker().noun() + " issue.",
            "System flagged transaction " + faker.finance().bic() + " for manual review due to unusual activity pattern."
        };
        return noteTemplates[random.nextInt(noteTemplates.length)];
    }

    public static UserInteractionEvent generateUserInteractionEvent(Faker faker, Random random, String existingSessionId, String existingUserId, LocalDateTime baseTimestamp) {
        Map<String, String> customAttributes = new HashMap<>();
        customAttributes.put("source", "generated_interaction");
        customAttributes.put("experiment_group", random.nextBoolean() ? "A" : "B");

        String sessionId = existingSessionId != null ? existingSessionId : faker.internet().uuid();
        String userId = existingUserId != null ? existingUserId : faker.internet().uuid();
        LocalDateTime eventTimestamp = baseTimestamp.plusSeconds(random.nextInt(60)); // Interaction within 60s of base

        return new UserInteractionEvent(
            faker.internet().uuid(),
            userId,
            sessionId,
            eventTimestamp,
            faker.options().option("product_view", "add_to_cart", "search", "page_load", "checkout_start", "item_impression", "filter_applied"),
            faker.commerce().productName(), // More realistic product name
            faker.commerce().department(), // More realistic category
            faker.internet().url(),
            faker.internet().userAgent(null), // Changed from userAgentAny()
            faker.internet().ipV4Address(),
            faker.options().option(faker.internet().url(), "direct", "internal_campaign_link"),
            customAttributes
        );
    }

    public static TransactionEvent generateTransactionEvent(Faker faker, Random random, List<String> preGeneratedComments, String existingSessionId, String existingUserId, LocalDateTime baseTimestamp) {
        List<String> productIds = Arrays.asList(
            faker.commerce().productName() + " (SKU: " + faker.idNumber().valid().substring(0,8) + ")",
            faker.commerce().productName() + " (SKU: " + faker.idNumber().valid().substring(0,8) + ")"
        );
        // SessionId is not directly part of TransactionEvent, but userId is.
        // Timestamp should be after the baseTimestamp (e.g., after some user interactions)
        String userId = existingUserId != null ? existingUserId : faker.internet().uuid();
        LocalDateTime eventTimestamp = baseTimestamp.plusMinutes(random.nextInt(5) + 1); // Transaction 1-5 mins after base

        return new TransactionEvent(
            faker.internet().uuid(), // transactionId
            faker.idNumber().valid(), // orderId
            userId,
            eventTimestamp,
            new BigDecimal(faker.commerce().price(10.00, 1000.00)), // Using String constructor for BigDecimal is safer
            faker.money().currencyCode(),
            faker.options().option("credit_card", "paypal", "apple_pay", "google_pay", "bank_transfer"),
            faker.options().option("completed", "pending", "failed", "refunded", "processing"),
            productIds,
            faker.address().streetAddress() + ", " + faker.address().city(), // shippingAddressId (using full address for realism)
            faker.address().streetAddress() + ", " + faker.address().city(), // billingAddressId
            faker.options().option(null, faker.commerce().promotionCode(), "SAVE" + faker.number().numberBetween(10,50)),
            faker.internet().url() + "/order/" + faker.idNumber().valid(),
            randomElement(preGeneratedComments, random)
        );
    }

    public static MerchantActionEvent generateMerchantActionEvent(Faker faker, Random random, List<String> preGeneratedComments, String relatedTransactionId, String existingUserId, LocalDateTime baseTimestamp) {
        // UserId might be relevant if the merchant action is tied to a specific user's transaction context.
        // Timestamp should be after the baseTimestamp (e.g., after a transaction)
        String staffUserId = existingUserId != null ? existingUserId : (faker.name().fullName() + " (Staff ID: " + faker.idNumber().validSvSeSsn().substring(0,6) + ")");
        LocalDateTime eventTimestamp = baseTimestamp.plusMinutes(random.nextInt(30) + 5); // Merchant action 5-30 mins after base

        return new MerchantActionEvent(
            faker.internet().uuid(), // actionId
            relatedTransactionId != null ? relatedTransactionId : faker.internet().uuid(),
            faker.company().name() + " (ID: " + faker.number().digits(5) + ")", // merchantId
            staffUserId,
            eventTimestamp,
            faker.options().option("order_shipped", "refund_processed", "inventory_updated", "customer_contacted", "payment_verified", "fraud_check_passed"),
            faker.options().option("success", "failed", "in_progress", "pending_review", "escalated"),
            // Replaced faker.logistics().trackingNumber() due to reported issues.
            faker.options().option(null, "UPS" + faker.random().hex(12).toUpperCase(), "FEDEX" + faker.random().hex(12).toUpperCase()),
            faker.options().option(null, faker.company().name(), "USPS", "DHL Express"),
            generateInternalNoteForMerchantAction(faker, random),
            faker.internet().url() + "/actions/" + faker.internet().uuid(),
            randomElement(preGeneratedComments, random)
        );
    }

    public static class UserInteractionEvent {
        private String eventId;
        private String userId;
        private String sessionId;
        private LocalDateTime timestamp;
        private String eventType; // e.g., "product_view", "add_to_cart", "search", "page_load"
        private String productId;
        private String categoryId;
        private String pageUrl;
        private String userAgent;
        private String ipAddress;
        private String referrerUrl;
        private Map<String, String> customAttributes; // For any other specific data

        // Constructors, Getters, and Setters

        public UserInteractionEvent(String eventId, String userId, String sessionId, LocalDateTime timestamp, String eventType, String productId, String categoryId, String pageUrl, String userAgent, String ipAddress, String referrerUrl, Map<String, String> customAttributes) {
            this.eventId = eventId;
            this.userId = userId;
            this.sessionId = sessionId;
            this.timestamp = timestamp;
            this.eventType = eventType;
            this.productId = productId;
            this.categoryId = categoryId;
            this.pageUrl = pageUrl;
            this.userAgent = userAgent;
            this.ipAddress = ipAddress;
            this.referrerUrl = referrerUrl;
            this.customAttributes = customAttributes;
        }

        // Getters and Setters for all fields (omitted for brevity but should be included)
        public String getEventId() { return eventId; }
        public String getUserId() { return userId; }
        public String getSessionId() { return sessionId; }
        public LocalDateTime getTimestamp() { return timestamp; }
        public String getEventType() { return eventType; }
        public String getProductId() { return productId; }
        public String getCategoryId() { return categoryId; }
        public String getPageUrl() { return pageUrl; }
        public String getUserAgent() { return userAgent; }
        public String getIpAddress() { return ipAddress; }
        public String getReferrerUrl() { return referrerUrl; }
        public Map<String, String> getCustomAttributes() { return customAttributes; }

        @Override
        public String toString() {
            StringJoiner joiner = new StringJoiner(",", "{", "}");
            joiner.add("\"eventId\":" + (eventId != null ? "\"" + escapeJson(eventId) + "\"" : "null"));
            joiner.add("\"userId\":" + (userId != null ? "\"" + escapeJson(userId) + "\"" : "null"));
            joiner.add("\"sessionId\":" + (sessionId != null ? "\"" + escapeJson(sessionId) + "\"" : "null"));
            joiner.add("\"timestamp\":" + (timestamp != null ? "\"" + timestamp.toString() + "\"" : "null"));
            joiner.add("\"eventType\":" + (eventType != null ? "\"" + escapeJson(eventType) + "\"" : "null"));
            joiner.add("\"productId\":" + (productId != null ? "\"" + escapeJson(productId) + "\"" : "null"));
            joiner.add("\"categoryId\":" + (categoryId != null ? "\"" + escapeJson(categoryId) + "\"" : "null"));
            joiner.add("\"pageUrl\":" + (pageUrl != null ? "\"" + escapeJson(pageUrl) + "\"" : "null"));
            joiner.add("\"userAgent\":" + (userAgent != null ? "\"" + escapeJson(userAgent) + "\"" : "null"));
            joiner.add("\"ipAddress\":" + (ipAddress != null ? "\"" + escapeJson(ipAddress) + "\"" : "null"));
            joiner.add("\"referrerUrl\":" + (referrerUrl != null ? "\"" + escapeJson(referrerUrl) + "\"" : "null"));

            String customAttributesJson = "null";
            if (customAttributes != null) {
                customAttributesJson = customAttributes.entrySet().stream()
                    .map(entry -> "\"" + escapeJson(entry.getKey()) + "\":" + (entry.getValue() != null ? "\"" + escapeJson(entry.getValue()) + "\"" : "null"))
                    .collect(Collectors.joining(",", "{", "}"));
            }
            joiner.add("\"customAttributes\":" + customAttributesJson);
            return joiner.toString();
        }
    }

    public static class TransactionEvent {
        private String transactionId;
        private String orderId;
        private String userId;
        private LocalDateTime transactionTimestamp;
        private BigDecimal totalAmount;
        private String currency;
        private String paymentMethod;
        private String transactionStatus; // e.g., "completed", "pending", "failed", "refunded"
        private List<String> productIds;
        private String shippingAddressId;
        private String billingAddressId;
        private String couponCode;
        private String transactionUrl; // URL to view the transaction details
        private String comment;

        // Constructors, Getters, and Setters

        public TransactionEvent(String transactionId, String orderId, String userId, LocalDateTime transactionTimestamp, BigDecimal totalAmount, String currency, String paymentMethod, String transactionStatus, List<String> productIds, String shippingAddressId, String billingAddressId, String couponCode, String transactionUrl, String comment) {
            this.transactionId = transactionId;
            this.orderId = orderId;
            this.userId = userId;
            this.transactionTimestamp = transactionTimestamp;
            this.totalAmount = totalAmount;
            this.currency = currency;
            this.paymentMethod = paymentMethod;
            this.transactionStatus = transactionStatus;
            this.productIds = productIds;
            this.shippingAddressId = shippingAddressId;
            this.billingAddressId = billingAddressId;
            this.couponCode = couponCode;
            this.transactionUrl = transactionUrl;
            this.comment = comment;
        }

        // Getters and Setters for all fields (omitted for brevity but should be included)
        public String getTransactionId() { return transactionId; }
        public String getOrderId() { return orderId; }
        public String getUserId() { return userId; }
        public LocalDateTime getTransactionTimestamp() { return transactionTimestamp; }
        public BigDecimal getTotalAmount() { return totalAmount; }
        public String getCurrency() { return currency; }
        public String getPaymentMethod() { return paymentMethod; }
        public String getTransactionStatus() { return transactionStatus; }
        public List<String> getProductIds() { return productIds; }
        public String getShippingAddressId() { return shippingAddressId; }
        public String getBillingAddressId() { return billingAddressId; }
        public String getCouponCode() { return couponCode; }
        public String getTransactionUrl() { return transactionUrl; }
        public String getComment() { return comment; }

        @Override
        public String toString() {
            StringJoiner joiner = new StringJoiner(",", "{", "}");
            joiner.add("\"transactionId\":" + (transactionId != null ? "\"" + escapeJson(transactionId) + "\"" : "null"));
            joiner.add("\"orderId\":" + (orderId != null ? "\"" + escapeJson(orderId) + "\"" : "null"));
            joiner.add("\"userId\":" + (userId != null ? "\"" + escapeJson(userId) + "\"" : "null"));
            joiner.add("\"transactionTimestamp\":" + (transactionTimestamp != null ? "\"" + transactionTimestamp.toString() + "\"" : "null"));
            joiner.add("\"totalAmount\":" + (totalAmount != null ? totalAmount.toPlainString() : "null"));
            joiner.add("\"currency\":" + (currency != null ? "\"" + escapeJson(currency) + "\"" : "null"));
            joiner.add("\"paymentMethod\":" + (paymentMethod != null ? "\"" + escapeJson(paymentMethod) + "\"" : "null"));
            joiner.add("\"transactionStatus\":" + (transactionStatus != null ? "\"" + escapeJson(transactionStatus) + "\"" : "null"));

            String productIdsJson = "null";
            if (productIds != null) {
                productIdsJson = productIds.stream()
                    .map(id -> id != null ? "\"" + escapeJson(id) + "\"" : "null")
                    .collect(Collectors.joining(",", "[", "]"));
            }
            joiner.add("\"productIds\":" + productIdsJson);

            joiner.add("\"shippingAddressId\":" + (shippingAddressId != null ? "\"" + escapeJson(shippingAddressId) + "\"" : "null"));
            joiner.add("\"billingAddressId\":" + (billingAddressId != null ? "\"" + escapeJson(billingAddressId) + "\"" : "null"));
            joiner.add("\"couponCode\":" + (couponCode != null ? "\"" + escapeJson(couponCode) + "\"" : "null"));
            joiner.add("\"transactionUrl\":" + (transactionUrl != null ? "\"" + escapeJson(transactionUrl) + "\"" : "null"));
            joiner.add("\"comment\":" + (comment != null ? "\"" + escapeJson(comment) + "\"" : "null"));
            return joiner.toString();
        }
    }

    public static class MerchantActionEvent {
        private String actionId;
        private String relatedTransactionId; // Links to the TransactionEvent
        private String merchantId;
        private String staffUserId; // ID of the staff member performing the action
        private LocalDateTime actionTimestamp;
        private String actionType; // e.g., "order_shipped", "refund_processed", "inventory_updated", "customer_contacted"
        private String status; // e.g., "success", "failed", "in_progress"
        private String trackingNumber;
        private String shippingCarrier;
        private String internalNotes;
        private String actionDetailsUrl; // URL to view more details about this merchant action
        private String comment; // Public or internal comment regarding the action

        // Constructors, Getters, and Setters

        public MerchantActionEvent(String actionId, String relatedTransactionId, String merchantId, String staffUserId, LocalDateTime actionTimestamp, String actionType, String status, String trackingNumber, String shippingCarrier, String internalNotes, String actionDetailsUrl, String comment) {
            this.actionId = actionId;
            this.relatedTransactionId = relatedTransactionId;
            this.merchantId = merchantId;
            this.staffUserId = staffUserId;
            this.actionTimestamp = actionTimestamp;
            this.actionType = actionType;
            this.status = status;
            this.trackingNumber = trackingNumber;
            this.shippingCarrier = shippingCarrier;
            this.internalNotes = internalNotes;
            this.actionDetailsUrl = actionDetailsUrl;
            this.comment = comment;
        }

        // Getters and Setters for all fields (omitted for brevity but should be included)
        public String getActionId() { return actionId; }
        public String getRelatedTransactionId() { return relatedTransactionId; }
        public String getMerchantId() { return merchantId; }
        public String getStaffUserId() { return staffUserId; }
        public LocalDateTime getActionTimestamp() { return actionTimestamp; }
        public String getActionType() { return actionType; }
        public String getStatus() { return status; }
        public String getTrackingNumber() { return trackingNumber; }
        public String getShippingCarrier() { return shippingCarrier; }
        public String getInternalNotes() { return internalNotes; }
        public String getActionDetailsUrl() { return actionDetailsUrl; }
        public String getComment() { return comment; }

        @Override
        public String toString() {
            StringJoiner joiner = new StringJoiner(",", "{", "}");
            joiner.add("\"actionId\":" + (actionId != null ? "\"" + escapeJson(actionId) + "\"" : "null"));
            joiner.add("\"relatedTransactionId\":" + (relatedTransactionId != null ? "\"" + escapeJson(relatedTransactionId) + "\"" : "null"));
            joiner.add("\"merchantId\":" + (merchantId != null ? "\"" + escapeJson(merchantId) + "\"" : "null"));
            joiner.add("\"staffUserId\":" + (staffUserId != null ? "\"" + escapeJson(staffUserId) + "\"" : "null"));
            joiner.add("\"actionTimestamp\":" + (actionTimestamp != null ? "\"" + actionTimestamp.toString() + "\"" : "null"));
            joiner.add("\"actionType\":" + (actionType != null ? "\"" + escapeJson(actionType) + "\"" : "null"));
            joiner.add("\"status\":" + (status != null ? "\"" + escapeJson(status) + "\"" : "null"));
            joiner.add("\"trackingNumber\":" + (trackingNumber != null ? "\"" + escapeJson(trackingNumber) + "\"" : "null"));
            joiner.add("\"shippingCarrier\":" + (shippingCarrier != null ? "\"" + escapeJson(shippingCarrier) + "\"" : "null"));
            joiner.add("\"internalNotes\":" + (internalNotes != null ? "\"" + escapeJson(internalNotes) + "\"" : "null"));
            joiner.add("\"actionDetailsUrl\":" + (actionDetailsUrl != null ? "\"" + escapeJson(actionDetailsUrl) + "\"" : "null"));
            joiner.add("\"comment\":" + (comment != null ? "\"" + escapeJson(comment) + "\"" : "null"));
            return joiner.toString();
        }
    }
}