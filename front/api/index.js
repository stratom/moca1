const express = require('express');
const routes = require('./src/routes/chatbotRoutes'); // ✅ nombre correcto

const app = express();
const port = 5000;

app.use(express.json());
app.use('/api/v1', routes);

app.listen(port, () => {
  console.log(`✅ Servidor escuchando en http://localhost:${port}`);
});



