const express = require('express');
const router = express.Router();
const { askChatbot } = require('../controllers/chatbotController');

router.post('/chatbot', askChatbot);

module.exports = router;



