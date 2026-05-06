const fs = require('fs');
const path = require('path');

const filepath = path.join(__dirname, 'tornado-control-center', 'dist', 'assets', 'index-BiPwywWC.js');
console.log('Patching React file at:', filepath);

let jsCode = fs.readFileSync(filepath, 'utf8');

const targetStr = 'margin:0},children:j';

// Let's replace the raw text node 'children:j' with an array rendering a custom span for the prefix (split by colon ':')
// Tailwind classes for 25% larger text and bold: 'text-lg font-bold text-[#e1e7ef] inline-block mb-1' + 'block mb-1' to put it on its own line if wanted, or inline.
const replacement = 'margin:0},children:[k.jsx("span",{className:"text-lg font-bold text-[#e1e7ef] block mb-1",children:j.split(":")[0]+":"}), j.substring(j.indexOf(":")+1)]';

if (jsCode.includes(targetStr)) {
    let newCode = jsCode.replace(targetStr, replacement);
    fs.writeFileSync(filepath, newCode, 'utf8');
    console.log('SUCCESS: React UI patched successfully to enlarge Winner name by 25% in bold!');
} else {
    // Already patched or cannot find string
    if (jsCode.includes('children:j.split(":")')) {
        console.log('NOTICE: React UI was already patched.');
    } else {
        console.error('ERROR: Could not find target React component string to patch.');
    }
}
