const { SerialPort, ReadlineParser } = require("serialport");

const ports = [
  new SerialPort({
    path: '/dev/ttyACM0',
    manufacturer: 'Adafruit',
    serialNumber: 'DF6310711B640F38',
    baudRate: 9600
  }),
  new SerialPort({
    path: '/dev/ttyACM1',
    manufacturer: 'Adafruit',
    serialNumber: 'DF6310711B6E2537',
    baudRate: 9600
  }),
  new SerialPort({
    path: '/dev/ttyACM2',
    manufacturer: 'Adafruit',
    serialNumber: 'DF6310711B41482E',
    baudRate: 9600
  }),
  new SerialPort({
    path: '/dev/ttyACM3',
    manufacturer: 'Adafruit',
    serialNumber: 'DF6310711B714936',
    baudRate: 9600
  })
];

const parser1 = ports[0].pipe(new ReadlineParser());
const parser2 = ports[1].pipe(new ReadlineParser());
const parser3 = ports[2].pipe(new ReadlineParser());
const parser4 = ports[3].pipe(new ReadlineParser());

ports[0].open(function (err) {
  if (err) {
    return console.log('Error opening port: ', err.message)
  }
});
ports[1].open(function (err) {
  if (err) {
    return console.log('Error opening port: ', err.message)
  }
});
ports[2].open(function (err) {
  if (err) {
    return console.log('Error opening port: ', err.message)
  }
});
ports[3].open(function (err) {
  if (err) {
    return console.log('Error opening port: ', err.message)
  }
});

ports[0].on('open', function() {
  console.log('---- opening 1');

  setTimeout(() => {
    ports[0].write('HELP\n');
    ports[0].write('CLEAR\n');
  }, 0);
  
  setTimeout(() => {
    ports[0].write('STOP\n');
  }, 1000);
  
  setTimeout(() => {
    ports[0].write('OFF\n');
  }, 2000);
});

ports[1].on('open', function() {
  console.log('---- opening 2');
  setTimeout(() => {
    ports[1].write('HELP\n');
    ports[1].write('CLEAR\n');
  }, 0);
  
  setTimeout(() => {
    ports[1].write('STOP\n');
  }, 1000);
  
  setTimeout(() => {
    ports[1].write('OFF\n');
  }, 2000);
});

ports[2].on('open', function() {
  console.log('---- opening 3');
  setTimeout(() => {
    ports[2].write('HELP\n');
    ports[2].write('CLEAR\n');
  }, 0);
  
  setTimeout(() => {
    ports[2].write('STOP\n');
  }, 1000);
  
  setTimeout(() => {
    ports[2].write('OFF\n');
  }, 2000);
});

ports[3].on('open', function() {
  console.log('---- opening 4');
  setTimeout(() => {
    ports[3].write('HELP\n');
    ports[3].write('CLEAR\n');
  }, 0);
  
  setTimeout(() => {
    ports[3].write('STOP\n');
  }, 1000);
  
  setTimeout(() => {
    ports[3].write('OFF\n');
  }, 2000);
});

parser1.on('data', console.log);
parser2.on('data', console.log);
parser3.on('data', console.log);
parser4.on('data', console.log);
