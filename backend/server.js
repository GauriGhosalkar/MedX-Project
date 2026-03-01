const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const User = require('./models/user');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// MongoDB Connection
mongoose.connect('mongodb://127.0.0.1:27017/medx_db')
    .then(() => console.log("Connected to MongoDB"))
    .catch(err => console.log("DB Connection Error:", err));

// --- API ROUTES ---

// 1. Register Route
app.post('/api/register', async (req, res) => {
    try {
        const { username, email, password } = req.body;

        // Check if user exists
        const existingUser = await User.findOne({ $or: [{ username }, { email }] });
        if (existingUser) return res.status(400).json({ message: "User already exists" });

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        const newUser = new User({ username, email, password: hashedPassword });
        await newUser.save();

        res.status(201).json({ 
            user: { u: newUser.username, e: newUser.email },
            message: "Registration successful" 
        });
    } catch (err) {
        res.status(500).json({ message: "Server error during registration" });
    }
});

// 2. Login Route
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        const user = await User.findOne({ username });
        if (!user) return res.status(400).json({ message: "Invalid credentials" });

        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) return res.status(400).json({ message: "Invalid credentials" });

        res.json({ 
            user: { u: user.username, e: user.email },
            message: "Login successful" 
        });
    } catch (err) {
        res.status(500).json({ message: "Server error during login" });
    }
});

app.listen(5000, () => console.log("Server running on port 5000"));