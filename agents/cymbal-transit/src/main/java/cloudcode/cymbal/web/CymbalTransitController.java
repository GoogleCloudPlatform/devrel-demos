/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package cloudcode.cymbal.web;

import com.google.cloud.mcp.McpToolboxClient;
import cloudcode.cymbal.CymbalTransitApplication;
import com.google.cloud.mcp.AuthTokenGetter;
import com.google.auth.oauth2.GoogleCredentials;
import com.google.auth.oauth2.IdTokenProvider;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Value;

import javax.annotation.PostConstruct;
import javax.servlet.http.HttpSession;
import java.io.FileInputStream;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// LangChain4j Imports for Agentic Routing & Gemini 3 Flash
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.vertexai.VertexAiGeminiChatModel;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.agent.tool.Tool;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.MemoryId;
import dev.langchain4j.service.UserMessage;

@SpringBootApplication
public class CymbalTransitController {
    public static void main(String[] args) {
        SpringApplication.run(CymbalTransitApplication.class, args);
    }
}

/**
 * 1. AI AGENT CONFIGURATION
 * Configures Gemini 3 Flash and binds it to our LangChain4j Agent Interface.
 */
@Configuration
class AgentConfiguration {

    @Value("${GCP_PROJECT_ID:fallback_project_id}")
    private String projectId;

    @Value("${GCP_REGION:fallback_region}")
    private String region;

    @Value("${GEMINI_MODEL_NAME:fallback_model}")
    private String modelName;

    @Bean
    ChatLanguageModel geminiChatModel() {
        return VertexAiGeminiChatModel.builder()
            .project(projectId)
            .location(region)
            .modelName(modelName) // Utilizing externalized parameters
            .build();
    }

    @Bean
    TransitAgent transitAgent(ChatLanguageModel chatLanguageModel, TransitAgentTools tools) {
        return AiServices.builder(TransitAgent.class)
            .chatLanguageModel(chatLanguageModel)
            .chatMemoryProvider(memoryId -> MessageWindowChatMemory.withMaxMessages(20))
            .tools(tools) // Exposes our MCP tools to Gemini
            .build();
    }
}

/**
 * 2. THE AI AGENT INTERFACE
 * Declarative AI service handling routing logic via System Prompt.
 */
interface TransitAgent {
    @SystemMessage({
        "You are the Cymbal Transit Concierge.",
        "CRITICAL INSTRUCTION: On your very first interaction, you MUST use the 'findAllSchedules' tool to fetch and memorize the broad bus routes.",
        "Keep this data handy in your context. Answer general routing questions using this stored data. ",
        "If you have to list the route details to the user, show it along with the full UUID and with other details that are meaningful. If the user chooses to book ticket as the next step, prompt them to copy the correct UUID nad paste so the transaction can be confirmed.",
        "ONLY if the user asks a specifically narrowed-down question, asks for precise times, or assigns a booking task, or asks about policies should you route to the specific tools like 'querySchedules', 'bookTicket', 'searchPolicies'.",
        "Remember the tool 'querySchedules' is for finding schedules between cities, 'bookTicket' is for booking ticket actionable between 2 cities,  'searchPolicies' is for finding matching policies for this company.",
        "Be intuitive and intelligent in finding the context even when user has typos. Do no hallucinate and make up stuff though. USe only data from the tools. ",
        "Don't show any asterisks while listing results. Keep it formatted and numbered or bulleted. asterisks distract."
    })
    String chat(@MemoryId String sessionId, @UserMessage String userMessage);
}

/**
 * 3. THE TOOLBOX BRIDGE
 * Wraps our asynchronous MCP Client calls into synchronous @Tools that LangChain4j (Gemini) can execute.
 */
@Service
class TransitAgentTools {
    
    private final McpToolboxService mcpService;

    public TransitAgentTools(McpToolboxService mcpService) {
        this.mcpService = mcpService;
    }

    @Tool("Fetches the initial, broad dataset of all available bus schedules and routes. Use this to build your context.")
    public String findAllSchedules() {
        return mcpService.findAllSchedules().join();
    }

    @Tool("Query specific schedules between an origin and destination city. Use only when the user narrows down their request.")
    public String querySchedules(String origin, String destination) {
        return mcpService.querySchedules(origin, destination).join();
    }

    @Tool("Book a ticket for a passenger using a specific trip ID.")
    public String bookTicket(String tripId, String passengerName) {
        return mcpService.bookTicket(tripId, passengerName).join();
    }

    @Tool("Semantic search for transit policies regarding luggage, pets, refunds, and general rules.")
    public String searchPolicies(String searchQuery) {
        return mcpService.searchPolicies(searchQuery).join();
    }
}

/**
 * 4. THE MCP TOOLBOX SERVICE
 * Handles the actual connection and execution against the AlloyDB backend.
 */
@Service
class McpToolboxService {
    
    private McpToolboxClient mcpClient;
    private String idToken;

    @Value("${MCP_TOOLBOX_URL:fallback_toolbox_url}")
    private String targetUrl;

    @PostConstruct
    public void init() {
        try {
            String tokenAudience = targetUrl; 
            
            System.out.println("--- Initializing MCP Toolbox Client ---");

            GoogleCredentials credentials = GoogleCredentials.getApplicationDefault();
            if (!(credentials instanceof IdTokenProvider)) {
                throw new RuntimeException("Loaded credentials do not support ID Tokens.");
            }

            this.idToken = ((IdTokenProvider) credentials)
                .idTokenWithAudience(tokenAudience, Collections.emptyList())
                .getTokenValue();

            this.mcpClient = McpToolboxClient.builder()
                .baseUrl(targetUrl)
                .apiKey(idToken) 
                .build();

            mcpClient.listTools().thenAccept(tools -> {
                System.out.println("Successfully discovered " + tools.size() + " tools.");
            }).join();

        } catch (Exception e) {
            System.err.println("Failed to initialize MCP Toolbox Client:");
            e.printStackTrace();
        }
    }

    public CompletableFuture<String> findAllSchedules() {
        return mcpClient.invokeTool("find-bus-schedules", Collections.emptyMap()).thenApply(result -> {
            if (result.isError() || result.content() == null || result.content().isEmpty()) return "No schedules found.";
            return result.content().get(0).text();
        });
    }

    public CompletableFuture<String> querySchedules(String origin, String destination) {
        java.util.Map<String, Object> params = new java.util.HashMap<>();
        params.put("origin", origin);
        params.put("destination", destination);

        return mcpClient.invokeTool("query-schedules", params).thenApply(result -> {
            if (result.isError() || result.content() == null || result.content().isEmpty()) return "No specific schedules found.";
            System.out.println(result);
            return result.content().get(0).text();
        });
    }

    public CompletableFuture<String> bookTicket(String tripId, String passengerName) {
        AuthTokenGetter toolAuthGetter = () -> CompletableFuture.completedFuture(idToken);
        return mcpClient.loadTool("book-ticket", Collections.singletonMap("google_auth", toolAuthGetter))
            .thenCompose(tool -> {
                tool.bindParam("passenger_name", passengerName);
                return tool.execute(Collections.singletonMap("trip_id", tripId));
            })
            .thenApply(result -> {
                if (result.isError() || result.content() == null || result.content().isEmpty()) return "Transaction failed.";
                return result.content().get(0).text();
            });
    }

    public CompletableFuture<String> searchPolicies(String searchQuery) {
        return mcpClient.invokeTool("search-policies", Map.of("search_query", searchQuery))
            .thenApply(result -> {
                if (result.isError() || result.content() == null || result.content().isEmpty()) return "No policy information found.";
                return result.content().get(0).text();
            });
    }
}

/**
 * 5. THE REST CONTROLLER
 * Now radically simplified! No more manual if/else logic or JSON parsing.
 */
@RestController
@RequestMapping("/api/agent")
class TransitAgentController {

    private final TransitAgent transitAgent;

    public TransitAgentController(TransitAgent transitAgent) {
        this.transitAgent = transitAgent;
    }

    @PostMapping("/chat")
    public ResponseEntity<String> handleUserChat(@RequestBody String userMessage, HttpSession session) {
        // We use the HTTP Session ID to tell LangChain4j which memory context to load
        String sessionId = session.getId();
        
        // Let Gemini 3 Flash handle the thinking, tool execution, and response generation!
        String agentResponse = transitAgent.chat(sessionId, userMessage);
        
        return ResponseEntity.ok(agentResponse);
    }
}