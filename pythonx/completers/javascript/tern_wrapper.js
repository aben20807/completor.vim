const tern = require('tern');
const readline = require('readline');
const fs = require('fs');

const log_file = fs.createWriteStream('js.log', {flags: 'w'});

function log(msg) {
  log_file.write(msg + '\n');
}

const rl = readline.createInterface({
  input: process.stdin,
  output: null,
  historySize: 0,
  terminal: false
});

var server = new tern.Server({ async: true });

function get_completions(filename, line, col, data) {
  var query = {
    type: 'completions',
    types: true,
    docs: true,
    file: '#0',
    filter: true,
    expandWordForward: false,
    end: {line: line, ch: col},
  };
  var file = {
    type: 'full',
    name: filename,
    text: data,
  };
  var doc = {query: query, files: [file]};
  server.request(doc, (err, res) => {
    var info = [];
    for (var i = 0; i < res.completions.length; i++) {
      const completion = res.completions[i];
      var comp = {word: completion.name, menu: completion.type};

      if (completion.guess) {
        comp.menu += ' ' + completion.guess;
      }

      if (completion.doc) {
        comp.info = completion.doc;
      }

      info.push(comp);
    }
    console.log(JSON.stringify(info));
  });
}

function run() {
  rl.on('line', (line) => {
    try {
      var input = JSON.parse(line);
      get_completions(input.filename, input.line, input.col, input.content);
    } catch (e) {
      return;
    }
  });
}

run();
