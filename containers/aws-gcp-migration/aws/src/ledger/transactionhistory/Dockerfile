FROM openjdk:17-jdk-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Package the application
RUN ./mvnw package -DskipTests

# Expose the port the application runs on
EXPOSE 8080

# Command to run the executable jar
CMD ["java", "-jar", "/app/target/transactionhistory-1.0.jar"]