const express = require('express');
const cors = require('cors');
const axios = require('axios');
const { GoogleAuth } = require('google-auth-library');

const app = express();
const port = 8081;

const TARGET_URL = 'https://dataprep-backend-199107193868.us-central1.run.app';

const auth = new GoogleAuth();
let idTokenClient;

app.use(cors()); // Enable CORS for all routes
app.use(express.json());

app.use('/api', async (req, res) => {
  try {
    if (!idTokenClient) {
      console.log('Initializing Google Auth client...');
      idTokenClient = await auth.getIdTokenClient(TARGET_URL);
      console.log('Auth client initialized.');
    }
    const token = await idTokenClient.idTokenProvider.fetchIdToken(TARGET_URL);

    const targetRequestUrl = `${TARGET_URL}${req.originalUrl}`;
    console.log(`Proxying ${req.method} to ${targetRequestUrl}`);

    // We will only forward a minimal set of headers to avoid issues.
    const headers = {
      'Authorization': `Bearer ${token}`,
      'host': new URL(TARGET_URL).hostname,
      'user-agent': req.headers['user-agent'],
      'accept': req.headers['accept'],
      'accept-encoding': req.headers['accept-encoding'],
      'accept-language': req.headers['accept-language'],
    };
    if (req.headers['content-type']) {
        headers['content-type'] = req.headers['content-type'];
    }


    const response = await axios({
      method: req.method,
      url: targetRequestUrl,
      headers: headers,
      data: req.body,
      responseType: 'stream'
    });

    res.status(response.status);
    Object.keys(response.headers).forEach((key) => {
        res.setHeader(key, response.headers[key]);
    });
    response.data.pipe(res);

  } catch (error) {
    console.error(`Error in proxy: ${error.message}`);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      res.status(error.response.status);
      Object.keys(error.response.headers).forEach((key) => {
          res.setHeader(key, error.response.headers[key]);
      });
      // Stream the error response body back to the client
      error.response.data.pipe(res);
    } else if (error.request) {
      // The request was made but no response was received
      res.status(504).send('Proxy request timed out.');
    } else {
      // Something happened in setting up the request that triggered an Error
      res.status(500).send('An error occurred in the proxy server.');
    }
  }
});

app.listen(port, () => {
  console.log(`Proxy server listening at http://localhost:${port}`);
});