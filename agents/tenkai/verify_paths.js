const fs = require('fs');
const path = require('path');

async function testCreateScenario() {
    const payload = {
        name: "Test Scenario " + Date.now(),
        description: "A scenario created by verification script",
        prompt: "# Verification Task\n\nPlease verify that this scenario works."
    };

    console.log("Testing POST /api/scenarios...");

    // We can't easily call the Next.js API route directly without the server running,
    // but we can simulate the logic or check if the implementation looks correct.
    // However, I can try to run the server if needed, but it's usually better to 
    // rely on visual verification in the browser tool if possible, 
    // or just check the file system logic.

    // Let's check if my path logic is sound by simulating it here.
    const rootDir = fs.existsSync(path.join(process.cwd(), 'scenarios')) ? process.cwd() : path.join(process.cwd(), '..');
    console.log("Detected rootDir:", rootDir);
    console.log("Scenarios dir should be at:", path.join(rootDir, 'scenarios'));

    if (fs.existsSync(path.join(rootDir, 'scenarios'))) {
        console.log("✅ Scenarios directory found.");
    } else {
        console.log("❌ Scenarios directory NOT found.");
    }
}

testCreateScenario();
