# Demo App for MCP Toolbox Java SDK 0.1.0 

### Cymbal Bus Agent

##### 1. AlloyDB database and MCP Toolbox for AlloyDB for tools integration.
##### 2. Cloud Run for Toolbox Deployment and Application (agent deployment).
##### 3. LangChain4J library for the agent and LLM framework in a Spring Boot Application with Java 17.

#### AlloyDB Setup

##### Install AlloyDB Cluster and Instance
Once click setup here:
``` url
https://codelabs.developers.google.com/quick-alloydb-setup
```

##### Extensions
``` sql
-- Enable necessary extensions for AI semantic search and embedding generation
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;
```

##### Create Table DDL

``` sql
-- Table 1: Transit Policies (Unstructured Data for RAG)
CREATE TABLE transit_policies (
    policy_id SERIAL PRIMARY KEY,
    category VARCHAR(50),
    policy_text TEXT,
    policy_embedding vector(768) 
);

-- Table 2: Intercity Bus Schedules (Structured Data)
CREATE TABLE bus_schedules (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_city VARCHAR(100),
    destination_city VARCHAR(100),
    departure_time TIMESTAMP,
    arrival_time TIMESTAMP,
    available_seats INT DEFAULT 50,
    ticket_price DECIMAL(6,2)
);

-- Table 3: Booking Ledger (Transactional Action Data)
CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES bus_schedules(trip_id),
    passenger_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

##### Data Ingestion

``` sql
-- 1. Insert Unstructured Policies and GENERATE REAL EMBEDDINGS natively in AlloyDB
INSERT INTO transit_policies (category, policy_text, policy_embedding) 
VALUES 
('Pets', 'Service animals are always welcome. Small pets (under 25 lbs) are allowed in secure carriers for a $25 fee. Large dogs are not permitted on standard coaches.', embedding('text-embedding-005', 'Service animals are always welcome. Small pets (under 25 lbs) are allowed in secure carriers for a $25 fee. Large dogs are not permitted on standard coaches.')),
('Luggage', 'Each passenger is allowed one carry-on (up to 15 lbs) and two stowed bags (up to 50 lbs each) free of charge. Additional bags cost $15 each.', embedding('text-embedding-005', 'Each passenger is allowed one carry-on (up to 15 lbs) and two stowed bags (up to 50 lbs each) free of charge. Additional bags cost $15 each.')),
('Refunds', 'Tickets are fully refundable up to 24 hours before departure. Within 24 hours, tickets can be exchanged for travel credit only.', embedding('text-embedding-005', 'Tickets are fully refundable up to 24 hours before departure. Within 24 hours, tickets can be exchanged for travel credit only.'));
```

```
-- 2. Generate 200+ Realistic Schedules for the Next 7 Days using generate_series
INSERT INTO bus_schedules (origin_city, destination_city, departure_time, arrival_time, ticket_price, available_seats)
SELECT 
    origin,
    destination,
    -- Generate departures every 4 hours starting from tomorrow
    (CURRENT_DATE + 1) + (interval '4 hours' * seq) AS dep_time,
    (CURRENT_DATE + 1) + (interval '4 hours' * seq) + interval '4.5 hours' AS arr_time,
    ROUND((RANDOM() * 30 + 25)::numeric, 2) AS price, -- Random price between $25 and $55
    FLOOR(RANDOM() * 50 + 1) AS seats -- Random seats between 1 and 50
FROM 
    (VALUES 
        ('New York', 'Boston'), ('Boston', 'New York'),
        ('Philadelphia', 'Washington DC'), ('Washington DC', 'Philadelphia'),
        ('Seattle', 'Portland'), ('Portland', 'Seattle')
    ) AS routes(origin, destination)
CROSS JOIN generate_series(1, 40) AS seq; -- 6 routes * 40 time slots = 240 distinct trips ingested!
```

#### Tools.yaml
Check repo for file. 
Replace the placeholders represented by "*****" with your values in Tools.yaml file.
You can parameterize these values as environment variables.

#### Install Toolbox

``` bash
# see releases page for other versions
export VERSION=0.27.0
curl -L -o toolbox https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
chmod +x toolbox
```

#### Deploy Toolbox to Cloud Run
Follow all the steps in the documentation. Including the authentication part. This is critical.
``` url
https://googleapis.github.io/genai-toolbox/how-to/deploy_toolbox/
```

#### Clone this repo
Replace your environment variables locally in the controller class and run it locally. To run locally:
``` bash
mvn clean install -U
```
and

``` bash
mvn sprint-boot:run
```

or 

To directly deploy your agent to Cloud Run and test there:

``` bash
gcloud run deploy cymbal-transit --source . --set-env-vars GCP_PROJECT_ID=<<YOUR_PROJECT_ID>>,GCP_REGION=us-central1,GEMINI_MODEL_NAME=gemini-2.5-flash,MCP_TOOLBOX_URL=<<YOUR_MCP_TOOLBOX_URL>> --allow-unauthenticated
```
Replace the placeholder variables enclosed within <<>>.