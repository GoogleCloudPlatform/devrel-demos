console.log("Loading vm_updates.js!");

// Function to make a synchronous REST API call to the given URL
function newMakeAPICallSync(url) {
    // Create a new XMLHttpRequest object
    var xhr = new XMLHttpRequest();

    // Open a GET request to the given URL
    xhr.open("GET", url, false);

    // Set the response type to JSON
    // xhr.responseType = "json";

    // Send the request
    xhr.send();

    // Check if the request was successful
    if (xhr.status === 200) {
    // Return the response
        return xhr.response;
    } else {
    // An error occurred
        throw new Error("Error: " + xhr.status + " " + xhr.statusText);
    }
}

// Function to call a REST API and update the result in the table
function callApiAndUpdateResult(apiUrl, resultId) {
    // makeAPICall(apiUrl, function(response) {
    newMakeAPICallSync(apiUrl, function(response) {
        // Convert the response to a JSON string
        const jsonResponse = JSON.stringify(response);

        // Get the HTML element with the specified ID (resultId)
        const resultElement = document.getElementById(resultId);

        // Update the inner HTML of the element with the JSON string
        resultElement.innerHTML = jsonResponse;

        // Alternatively, you can also update the element's text content directly:
        // resultElement.textContent = jsonResponse;
        // document.getElementById(resultId).innerHTML = JSON.stringify(response);
    });
}

//// Function to make a Rest API request to the given URL
//function makeAPICall(url, callback) {
//    // Create a new XMLHttpRequest object
//    var xhr = new XMLHttpRequest();
//
//    // Open a GET request to the given URL
//    xhr.open("GET", url, true);
//
//    // Set the response type to JSON
//    xhr.responseType = "json";
//
//    // Send the request
//    xhr.send();
//
//    // Handle the response
//    xhr.onload = function() {
//        if (xhr.status === 200) {
//            // Call the callback function with the response
//            callback(xhr.response);
//        } else {
//            // An error occurred
//            console.error("Error: " + xhr.status + " " + xhr.statusText);
//        }
//    };
//    // Logging
//    console.log("Calling API!")
//}
