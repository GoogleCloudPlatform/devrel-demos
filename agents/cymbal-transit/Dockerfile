# 1. Build Stage: Use an official Maven image with Java 17
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

# Copy the pom.xml and source code
COPY pom.xml .
COPY src ./src

# Compile and package the application (skipping tests for faster deployment)
RUN mvn clean package -DskipTests

# 2. Run Stage: Use a lightweight Java 17 JRE image to run the app
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

# Copy the compiled JAR file from the build stage
COPY --from=build /app/target/*.jar app.jar

# Expose the standard web port
EXPOSE 8080

# Run the Spring Boot application
ENTRYPOINT ["java", "-jar", "app.jar"]