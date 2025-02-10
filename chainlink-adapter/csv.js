const fs = require('fs');
const readline = require('readline');
const path = require('path');

const csvFilePath = path.join(__dirname, 'federated_learning_results.csv');
const jsonFilePath = path.join(__dirname, 'mock-data.json');

async function processCSV() {
  const fileStream = fs.createReadStream(csvFilePath);
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity
  });
  
  let averageNMSE;
  
  for await (const line of rl) {
    // Assuming the first line is headers and data starts from the second line
    const columns = line.split(',');
    if (columns[0] === 'Round Number') continue; // Skip header row
    
    averageNMSE = columns[3]; // Assuming 'Average NMSE' is in the fourth column
    break; // Stop after the first data row
  }
  
  // Write to JSON file
  try {
    fs.writeFileSync(jsonFilePath, JSON.stringify({ "AverageNMSE": parseFloat(averageNMSE) }, null, 2));
    console.log(`mock-data.json has been updated with Average NMSE value.`);
  } catch (error) {
    console.error('Error writing file:', error);
  }
}

processCSV();
