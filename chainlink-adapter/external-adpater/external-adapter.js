 
// external-adapter.js
const express = require('express');
const request = require('request');

const app = express();
app.use(express.json());

const externalJobId = '293676225a0e49ec9828b2cb593dcf39';

app.post('/fulfill', (req, res) => {
  const data = req.body.data;
  const apiEndpoint = 'http://localhost:3000/data'; // Change this URL to the real API endpoint

  request(apiEndpoint, (error, apiResponse, body) => {
    if (error) {
      console.error('Error:', error);
      return res.status(500).json({ error: 'Error while fetching data from the API' });
    }
  
    const responseData = JSON.parse(body);
    const customData = responseData.value; // Adjusted from responseData.data to responseData.value
  
    const response = {
      jobRunID: data.id,
      data: {
        data: customData, // This structure is fine as long as your contract expects it this way
      },
      result: customData,
      statusCode: 200,
    };
  
    res.status(200).json(response);
  });
  
});

const port = 8080;
app.listen(port, () => {
  console.log(`External adapter is running on port ${port}`);
});
