const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.post('/api/chat', async (req, res) => {
    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: "Query is required" });
    }

    console.log(`\n[API] Processing Query: "${query}"`);

    // Resolve the path to the legal_agent.py (one level up from backend/)
    console.log(`[API] Forwarding to FastAPI: http://localhost:8000/api/chat`);

    try {
        const response = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`FastAPI Error: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        return res.json(result);

    } catch (error) {
        console.error("\n[API] Error calling Python FastAPI microservice:", error.message);
        return res.status(500).json({
            error: "Python microservice execution failed",
            details: error.message
        });
    }
});

app.listen(PORT, () => {
    console.log(`=========================================`);
    console.log(`🚀 Accenture Legal Bot API Server`);
    console.log(`📡 URL: http://localhost:${PORT}`);
    console.log(`=========================================`);
});
