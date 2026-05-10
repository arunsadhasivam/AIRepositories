# Ollama4j Tool Calling — Player DB Query

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
    <groupId>io.github.ollama4j</groupId>
    <artifactId>ollama4j</artifactId>
    <version>1.0.79</version>
</dependency>
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>runtime</scope>
</dependency>
```

## application.yml

```yaml
ollama:
  model: mistral
  host: http://localhost:11434
  timeout: 60

spring:
  datasource:
    url: jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1
    driver-class-name: org.h2.Driver
    username: sa
    password:
  jpa:
    hibernate:
      ddl-auto: create-drop
  h2:
    console:
      enabled: true
```

> **Note:** Use 2-space indentation in yml — `@Value` will not load if indentation is wrong.

---

## OllamaConfig.java

```java
@Configuration
public class OllamaConfig {

    @Value("${ollama.host}")
    private String host;

    @Value("${ollama.timeout}")
    private int timeout;

    // registers OllamaAPI as Spring bean — autowired in AgentService
    @Bean
    public OllamaAPI ollamaAPI() {
        OllamaAPI api = new OllamaAPI(host);
        api.setRequestTimeoutSeconds(timeout);
        return api;
    }
}
```

---

## PlayerToolFunction.java

```java
@Component
public class PlayerToolFunction implements ToolFunction {

    // Spring injects PlayerRepository via constructor
    private final PlayerRepository playerRepository;

    public PlayerToolFunction(PlayerRepository playerRepository) {
        this.playerRepository = playerRepository;
    }

    @Override
    public Object apply(Map<String, Object> arguments) {

        // Ollama extracts 'birthCountry' from user question and passes it here
        // key must match withProperty("birthCountry") in ToolSpecFactory
        String birthCountry = arguments.get("birthCountry").toString();

        // query DB using JpaRepository — no SQL needed
        List<Player> playerList = playerRepository.findByBirthCountry(birthCountry);

        // if no results return message back to Ollama
        if (playerList.isEmpty()) {
            return Map.of("message", "No players found in: " + birthCountry);
        }

        // use HashMap — Map.of() does not allow null values
        // stream iterates each Player object one by one
        // map() converts each Player to Map<String, String>
        // collect() gathers all maps into final List
        List<Map<String, String>> result = playerList.stream()
            .map(p -> {
                Map<String, String> map = new HashMap<>();
                map.put("playerId",     p.getPlayerId()     != null ? p.getPlayerId()     : "");
                map.put("country",      p.getBirthCountry() != null ? p.getBirthCountry() : "");
                map.put("Name",         p.getGivenName()    != null ? p.getGivenName()    : "");
                return map;
            })
            .collect(Collectors.toList());

        return result;
    }
}
```

---

## ToolSpecFactory.java

```java
@Component
public class ToolSpecFactory {

    // Spring injects PlayerToolFunction via @Autowired
    @Autowired
    private PlayerToolFunction playerToolFunction;

    public Tools.ToolSpecification playerTool() {

        return Tools.ToolSpecification.builder()

            // internal label Ollama uses to identify this tool
            // never referenced in your Java code
            .functionName("getPlayerDetailsByBirthCountry")

            // Ollama reads this to decide WHEN to call the tool
            // based on user question — more descriptive = better tool selection
            .functionDescription("Retrieve player with birthCountry provided")

            // attach PlayerToolFunction — Ollama calls apply() when tool is triggered
            // toolDefinition must come before properties in builder chain
            .toolDefinition(playerToolFunction)

            // PropsBuilder defines parameters Ollama extracts from user question
            .properties(
                new Tools.PropsBuilder()

                    // "birthCountry" must match arguments.get("birthCountry") in PlayerToolFunction
                    .withProperty("birthCountry",
                        Tools.PromptFuncDefinition.Property.builder()
                            .type("string")                          // Ollama extracts as String
                            .description("find player birthCountry matches")
                            .required(true)                          // Ollama must find this before calling tool
                            .build())

                    .build()  // returns Map<String, Property>
            )
            .build();  // returns final ToolSpecification
    }
}
```

---

## AgentService.java

```java
@Service
public class AgentService {

    @Autowired
    private OllamaAPI ollamaAPI;

    @Autowired
    private ToolSpecFactory toolSpecFactory;

    @Value("${ollama.model}")
    private String model;

    @SuppressWarnings("unchecked")
    public Optional<List<Map<String, String>>> ask(String query) throws Exception {

        // Step 1: build tool spec with PlayerToolFunction attached
        Tools.ToolSpecification tool = toolSpecFactory.playerTool();

        // Step 2: register tool with OllamaAPI instance
        ollamaAPI.registerTool(tool);

        // Step 3: PromptBuilder embeds tool spec into prompt
        // format: [AVAILABLE_TOOLS]...[/AVAILABLE_TOOLS][INST] query [/INST]
        String prompt = new Tools.PromptBuilder()
            .withToolSpecification(tool)
            .withPrompt(query)
            .build();

        // Step 4: send to Ollama — model reads tool spec and calls PlayerToolFunction
        // response must contain [TOOL_CALLS] — only tool-capable models support this
        // use mistral / llama3.2 / qwen2.5 — quantized versions may not support tool calling
        OllamaToolsResult toolsResult = ollamaAPI.generateWithTools(
            model,
            prompt,
            new OptionsBuilder().build()
        );

        // Step 5: collect results from all tool executions
        List<Map<String, String>> finalResult = new ArrayList<>();
        for (OllamaToolsResult.ToolResult result : toolsResult.getToolResults()) {
            Object objResult = result.getResult();

            // instanceof check before cast — avoids ClassCastException
            if (objResult instanceof List<?>) {
                // unchecked cast — unavoidable when return type is Object
                // use @SuppressWarnings("unchecked") on method to suppress warning
                List<Map<String, String>> cur = (List<Map<String, String>>) objResult;
                finalResult.addAll(cur);  // merge each tool result into one list
            }
        }

        return Optional.of(finalResult);
    }
}
```

---

## Flow

```
User question → AgentService.ask()
                    ↓
        ToolSpecFactory.playerTool() — builds ToolSpecification
                    ↓
        PromptBuilder — embeds tool spec into prompt
                    ↓
        ollamaAPI.generateWithTools() — sends to mistral
                    ↓
        Ollama reads tool spec → extracts birthCountry from question
        returns [TOOL_CALLS] [{"name": "getPlayerDetailsByBirthCountry", "arguments": {"birthCountry": "USA"}}]
                    ↓
        ollama4j invokes PlayerToolFunction.apply({"birthCountry": "USA"})
                    ↓
        playerRepository.findByBirthCountry("USA") → List<Player>
                    ↓
        returns List<Map<String, String>> to Ollama
                    ↓
        AgentService collects and returns Optional<List<Map>>
```

---

## Key Rules

| Rule | Detail |
|---|---|
| Model must support tool calling | Use `mistral`, `llama3.2`, `qwen2.5` — quantized versions may fail |
| `functionName` | Ollama internal only — never referenced in Java code |
| `withProperty("birthCountry")` | Must match `arguments.get("birthCountry")` in `PlayerToolFunction` |
| `findByBirthCountry` | `findBy` + exact entity field name with uppercase first letter |
| `toolDefinition` before `properties` | Builder chain order matters in 1.0.79 |
| `Map.of()` vs `HashMap` | Use `HashMap` — `Map.of()` throws on null values |
| yml indentation | 2 spaces — `@Value` fails if indentation is wrong |
