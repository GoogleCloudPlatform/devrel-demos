# Java dockerfile for balancereader 
# Use an official OpenJDK runtime as a parent image
FROM openjdk:17-jdk-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Package the application
RUN ls
RUN ./mvnw package -DskipTests

# Expose the port the application runs on
EXPOSE 8080

# Command to run the executable jar
CMD ["java", "-jar", "target/balancereader-0.0.1-SNAPSHOT.jar"]