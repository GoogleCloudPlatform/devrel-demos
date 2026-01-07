package main

import "fmt"

const greetingMessage = "Hello from Tenkai"

func greeting() string {
	return greetingMessage
}

func main() {
	fmt.Println(greeting())
}
